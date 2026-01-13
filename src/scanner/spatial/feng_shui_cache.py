import json
import time

import requests
from rich.console import Console
from shapely.geometry import MultiPolygon, Point, Polygon, shape
from shapely.strtree import STRtree
from shapely.wkt import dumps, loads

from scanner.db import get_session
from scanner.models import CachedFengShui

console = Console()

# WFS Config
WFS_URL = "https://opendata.maps.vic.gov.au/geoserver/wfs"
# Bounding Box (Melbourne Metro approx)
BBOX_MELBOURNE = [144.5, -38.2, 145.6, -37.4]


class FengShuiCache:
    def __init__(self):
        self.tree = None
        self.items = []  # (id, type, shape)

    def load_cache(self):
        """Load cached items into memory STRtree."""
        with get_session() as session:
            rows = session.query(CachedFengShui).all()
            if not rows:
                return

            geoms = []
            self.items = []
            for row in rows:
                try:
                    s = loads(row.geom_wkt)
                    geoms.append(s)
                    self.items.append(
                        {
                            "id": row.id,
                            "type": row.feature_type,
                            "attributes": row.attributes,
                            "geometry": s,
                        }
                    )
                except Exception:
                    continue

            if geoms:
                self.tree = STRtree(geoms)

    def check_proximity(self, lat, lon, feature_type, radius_m):
        """Check if point is within radius_m of feature_type."""
        if not self.tree:
            self.load_cache()
        if not self.tree:
            return False, None

        p = Point(lon, lat)
        # 1 deg lat ~ 111km -> 1km ~ 0.009 deg. 50m ~ 0.00045 deg
        buffer_deg = radius_m / 111111.0

        # Get candidates
        indices = self.tree.query(p.buffer(buffer_deg))

        for idx in indices:
            item = self.items[idx]
            if item["type"] == feature_type:
                dist_deg = p.distance(item["geometry"])
                dist_m = dist_deg * 111111  # Approx
                if dist_m <= radius_m:
                    return True, item

        return False, None


# Singleton instance
_feng_shui_cache = None


def get_cache():
    global _feng_shui_cache
    if _feng_shui_cache is None:
        _feng_shui_cache = FengShuiCache()
        _feng_shui_cache.load_cache()
    return _feng_shui_cache


def check_puz1_proximity(lat, lon, radius_m=50):
    """Check if point is near a PUZ1 zone (Substation proxy)."""
    cache = get_cache()
    return cache.check_proximity(lat, lon, "PUZ1", radius_m)


def check_water_proximity(lat, lon, radius_m=50):
    """Check if point is near a Water body (Reservoir)."""
    cache = get_cache()
    return cache.check_proximity(lat, lon, "WATER", radius_m)


def check_road_node_proximity(lat, lon, radius_m=20):
    """Check if point is near a road endpoint (T-junction proxy)."""
    cache = get_cache()
    return cache.check_proximity(lat, lon, "ROAD_NODE", radius_m)


def populate_puz1():
    """Populate Public Use Zone 1 (Service & Utility) cache."""
    console.print("[blue]Populating PUZ1 Cache (Substation proxy)...[/blue]")

    # Vicmap doesn't allow both bbox param and cql_filter.
    # We must put BBOX inside the CQL.
    # Assuming geometry column is 'geom' (standard for Vicmap).
    # NOTE: property names are case sensitive in CQL. Debug output showed 'zone_code'.
    cql = f"zone_code='PUZ1' AND BBOX(geom, {BBOX_MELBOURNE[0]}, {BBOX_MELBOURNE[1]}, {BBOX_MELBOURNE[2]}, {BBOX_MELBOURNE[3]})"

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:plan_zone",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "cql_filter": cql,
        "maxFeatures": 10000,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=60)
        # If this fails, it might be due to CQL.
        if resp.status_code != 200:
            console.print(f"[red]WFS Error: {resp.text[:200]}[/red]")
            return

        data = resp.json()
        features = data.get("features", [])
        console.print(f"[green]Found {len(features)} PUZ1 zones.[/green]")

        with get_session() as session:
            count = 0
            for f in features:
                fid = f["id"]
                props = f["properties"]
                geom = shape(f["geometry"])

                # Check exist
                if session.query(CachedFengShui).filter_by(feature_id=fid).first():
                    continue

                obj = CachedFengShui(
                    feature_id=fid,
                    feature_type="PUZ1",
                    attributes=props,
                    geom_wkt=dumps(geom),
                    bbox_min_lat=geom.bounds[1],
                    bbox_min_lon=geom.bounds[0],
                    bbox_max_lat=geom.bounds[3],
                    bbox_max_lon=geom.bounds[2],
                )
                session.add(obj)
                count += 1
            session.commit()
            console.print(f"[blue]Added {count} new PUZ1 zones.[/blue]")

    except json.JSONDecodeError:
        console.print(
            f"[red]JSON Decode Error. Response text:[/red]\n{resp.text[:500]}"
        )
    except Exception as e:
        console.print(f"[red]Error populating PUZ1: {e}[/red]")


def populate_road_endpoints():
    """Populate Road Endpoints (T-Junction candidates)."""
    console.print("[blue]Populating Road Cache (T-Junctions)...[/blue]")

    # Vicmap Transport Road
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:tr_road",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        # Use bbox param (simpler)
        "bbox": f"{BBOX_MELBOURNE[0]},{BBOX_MELBOURNE[1]},{BBOX_MELBOURNE[2]},{BBOX_MELBOURNE[3]},EPSG:4326",
        "maxFeatures": 50000,  # Roads are numerous
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        console.print(f"[green]Found {len(features)} road segments.[/green]")

        with get_session() as session:
            count = 0
            for f in features:
                fid = f["id"] + "_start"  # Store start and end separately
                fid_end = f["id"] + "_end"

                # Check exist (optimization)
                if session.query(CachedFengShui).filter_by(feature_id=fid).first():
                    continue

                geom = shape(f["geometry"])
                if geom.geom_type != "LineString":
                    continue

                # Extract Start and End points
                start_pt = Point(geom.coords[0])
                end_pt = Point(geom.coords[-1])

                # Add Start
                obj1 = CachedFengShui(
                    feature_id=fid,
                    feature_type="ROAD_NODE",
                    attributes={"original_id": f["id"]},
                    geom_wkt=dumps(start_pt),
                    bbox_min_lat=start_pt.y,
                    bbox_min_lon=start_pt.x,
                    bbox_max_lat=start_pt.y,
                    bbox_max_lon=start_pt.x,
                )

                # Add End
                obj2 = CachedFengShui(
                    feature_id=fid_end,
                    feature_type="ROAD_NODE",
                    attributes={"original_id": f["id"]},
                    geom_wkt=dumps(end_pt),
                    bbox_min_lat=end_pt.y,
                    bbox_min_lon=end_pt.x,
                    bbox_max_lat=end_pt.y,
                    bbox_max_lon=end_pt.x,
                )

                session.add(obj1)
                session.add(obj2)
                count += 2

                if count % 1000 == 0:
                    session.commit()

            session.commit()
            console.print(f"[blue]Added {count} road nodes.[/blue]")

    except Exception as e:
        console.print(f"[red]Error populating Road Nodes: {e}[/red]")


def populate_water():
    """Populate significant Water Bodies cache."""
    console.print("[blue]Populating Water Cache (Reservoirs)...[/blue]")
    # Vicmap Hydro

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:hy_water_area_polygon",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{BBOX_MELBOURNE[0]},{BBOX_MELBOURNE[1]},{BBOX_MELBOURNE[2]},{BBOX_MELBOURNE[3]},EPSG:4326",
        "maxFeatures": 5000,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        console.print(f"[green]Found {len(features)} water bodies.[/green]")

        with get_session() as session:
            count = 0
            for f in features:
                fid = f["id"]
                props = f["properties"]
                geom = shape(f["geometry"])

                if session.query(CachedFengShui).filter_by(feature_id=fid).first():
                    continue

                obj = CachedFengShui(
                    feature_id=fid,
                    feature_type="WATER",
                    attributes=props,
                    geom_wkt=dumps(geom),
                    bbox_min_lat=geom.bounds[1],
                    bbox_min_lon=geom.bounds[0],
                    bbox_max_lat=geom.bounds[3],
                    bbox_max_lon=geom.bounds[2],
                )
                session.add(obj)
                count += 1
            session.commit()
            console.print(f"[blue]Added {count} new water bodies.[/blue]")

    except Exception as e:
        console.print(f"[red]Error populating Water: {e}[/red]")


if __name__ == "__main__":
    populate_puz1()
    populate_water()
    populate_road_endpoints()
    populate_road_endpoints()
