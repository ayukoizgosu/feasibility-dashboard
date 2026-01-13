import math
from typing import Optional

import requests
from rich.console import Console
from shapely.geometry import LineString, Point, Polygon, shape

from scanner.spatial.feng_shui_cache import WFS_URL, get_cache

console = Console()


def calculate_approx_area_sqm(polygon: Polygon) -> float:
    """
    Calculate approximate area in square meters for a lat/lon polygon.
    Uses simple projection based on centroid latitude.
    """
    if not polygon:
        return 0.0

    centroid_lat = polygon.centroid.y
    lat_scale = 111111.0
    lon_scale = 111111.0 * math.cos(math.radians(centroid_lat))

    # Simple affine scaling approximation
    return polygon.area * lat_scale * lon_scale


def get_property_polygon(lat: float, lon: float) -> Polygon | None:
    """
    Fetch the property polygon at the given location from Vicmap WFS.
    Uses 'v_property_mp' (Property MultiPolygon).
    """
    # Use a small buffer to ensure intersection (point might be slightly off)
    # 0.0001 deg ~ 10m.
    # Actually, INTERSECTS(geom, POINT) is better.

    # Using 'v_property_mp'
    type_name = "open-data-platform:v_property_mp"

    # Try CQL Filter with different geometry column names
    # Vicmap uses various names: SHAPE, the_geom, geom, geometry
    geom_columns = ["SHAPE", "the_geom", "geom", "geometry"]

    for geom_col in geom_columns:
        cql = f"INTERSECTS({geom_col}, POINT({lon} {lat}))"

        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "cql_filter": cql,
            "maxFeatures": 1,
        }

        try:
            resp = requests.get(WFS_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    # Found it!
                    geom = shape(features[0]["geometry"])
                    if geom.geom_type == "MultiPolygon":
                        return max(geom.geoms, key=lambda a: a.area)
                    return geom
        except Exception:
            pass  # Try next column name

    # CQL failed with all column names - use BBOX fallback
    console.print(
        "[yellow]CQL Intersection failed (0 features). Trying BBOX fallback...[/yellow]"
    )

    # Fallback: BBOX query (small area)
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{lon-0.0001},{lat-0.0001},{lon+0.0001},{lat+0.0001},EPSG:4326",
        "maxFeatures": 5,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=30)
        data = resp.json()
        features = data.get("features", [])

        if features:
            console.print(
                f"[dim]Fallback found {len(features)} features. Geom name check...[/dim]"
            )
            # Find closest feature to point
            point = Point(lon, lat)
            best_g = None
            min_dist = float("inf")

            for f in features:
                g = shape(f["geometry"])
                d = g.distance(point)
                if d < min_dist:
                    min_dist = d
                    best_g = g

            # Tolerance ~15m (1.5e-4 degrees)
            if best_g and min_dist < 1.5e-4:
                if best_g.geom_type == "MultiPolygon":
                    return max(best_g.geoms, key=lambda a: a.area)
                return best_g

            console.print(
                f"[red]Fallback features too far (min dist: {min_dist}).[/red]"
            )

        return None

    except Exception as e:
        console.print(f"[red]Error fetching property polygon: {e}[/red]")
        return None


def _find_frontage_edge(
    parcel_poly: Polygon,
) -> tuple[int, float, float, list[LineString]]:
    """
    Helper to find the edge index that is the frontage.
    Returns (index, length_m, dist_to_road_m, road_lines).
    Index is -1 if no frontage found.
    """
    if not parcel_poly or parcel_poly.is_empty:
        return -1, 0.0, 0.0, []

    # 1. Get Roads
    cache = get_cache()
    if not cache.tree:
        cache.load_cache()

    minx, miny, maxx, maxy = parcel_poly.bounds

    # Simple WFS fetch for now (proven to work)
    road_lines = []
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:tr_road",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{minx-0.001},{miny-0.001},{maxx+0.001},{maxy+0.001},EPSG:4326",
    }

    try:
        r = requests.get(WFS_URL, params=params, timeout=10)
        d = r.json()
        feats = d.get("features", [])
        for f in feats:
            road_lines.append(shape(f["geometry"]))
    except:
        pass

    if not road_lines:
        return -1, 0.0, 0.0, []

    coords = list(parcel_poly.exterior.coords)
    limit = len(coords) - 1

    best_idx = -1
    max_len = 0.0
    min_dist_of_best = 999.0

    for i in range(limit):
        p1 = Point(coords[i])
        p2 = Point(coords[i + 1])
        edge = LineString([p1, p2])
        edge_len_m = edge.length * 111111

        midpoint = edge.interpolate(0.5, normalized=True)
        min_dist = float("inf")
        for road in road_lines:
            d = road.distance(midpoint) * 111111
            if d < min_dist:
                min_dist = d

        # Threshold 20m
        if min_dist < 20.0:
            if edge_len_m > max_len:
                max_len = edge_len_m
                best_idx = i
                min_dist_of_best = min_dist

    return best_idx, max_len, min_dist_of_best, road_lines


def calculate_frontage(parcel_poly: Polygon) -> tuple[float, list[str]]:
    """
    Calculate frontage length.
    """
    idx, length, dist, _ = _find_frontage_edge(parcel_poly)
    if idx != -1:
        return length, [f"Frontage Edge {idx}: {length:.1f}m (Dist: {dist:.1f}m)"]
    return 0.0, ["No frontage found (<20m to road)"]


def calculate_slope_and_elevation(parcel_poly: Polygon) -> tuple[float, float, str]:
    """
    Calculate average slope (%) and average elevation (m).
    Uses 'el_contour_1to5m' (Granular).
    """
    if not parcel_poly:
        return 0.0, 0.0, "Invalid Geometry"

    minx, miny, maxx, maxy = parcel_poly.bounds

    # Query Contours
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:el_contour_1to5m",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        # Slightly larger buffer to catch surrounding contours if parcel is between them
        "bbox": f"{minx-0.001},{miny-0.001},{maxx+0.001},{maxy+0.001},EPSG:4326",
    }

    elevations = []

    try:
        r = requests.get(WFS_URL, params=params, timeout=15)
        d = r.json()
        feats = d.get("features", [])

        for f in feats:
            # Check intersection or proximity to parcel
            g = shape(f["geometry"])
            # Use buffer intersection to catch nearby context
            if g.intersects(parcel_poly.buffer(0.0002)):  # ~20m buffer
                props = f["properties"]
                val = (
                    props.get("ALTITUDE")
                    or props.get("altitude")
                    or props.get("ELEVATION")
                )
                if val:
                    try:
                        elevations.append(float(val))
                    except:
                        pass

    except Exception as e:
        return 0.0, 0.0, f"Error fetching contours: {e}"

    if not elevations:
        return 0.0, 0.0, "No contour data found"

    min_el = min(elevations)
    max_el = max(elevations)
    avg_el = sum(elevations) / len(elevations)

    rise = max_el - min_el

    # Run calculation
    # Only consider the portion of the run covered by the elevation difference?
    # Conservative: Diagonal of the bounding box of the FOUND contours?
    # Or just Parcel Area sqrt?
    # If we fetched a larger area (buffer), using Parcel Area sqrt as run might overestimate slope if rise is from outside.
    # But we want the slope of the LAND.
    # Let's use the Diagonal Distance between the locations of Min and Max elevation?
    # Hard to get exact points from WFS lines without parsing coords.

    # Simple proxy: Use Parcel Diagonal Length (~sqrt(Area)*1.4)
    run = math.sqrt(parcel_poly.area) * 111111 * 1.2

    if run <= 0:
        return 0.0, avg_el, "Zero area"

    slope_pct = (rise / run) * 100

    return slope_pct, avg_el, f"Range: {min_el}-{max_el}m (Rise: {rise}m)"


def calculate_orientation(
    parcel_poly: Polygon, frontage_index: int = -1
) -> tuple[float, str]:
    """
    Calculate the bearing of the "Rear" of the property.
    Defined as the bearing of the vector NORMAL to the frontage, pointing INTO the block.
    """
    if not parcel_poly:
        return 0.0, "Invalid Geom"

    if frontage_index == -1:
        # Find it
        frontage_index, _, _, _ = _find_frontage_edge(parcel_poly)

    if frontage_index == -1:
        return 0.0, "No Frontage Found"

    coords = list(parcel_poly.exterior.coords)
    p1 = coords[frontage_index]
    p2 = coords[frontage_index + 1]

    # Frontage Vector (P1 -> P2)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    # Normal Vectors (perpendicular)
    # N1 = (-dy, dx)
    # N2 = (dy, -dx)

    midpoint = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)

    # Test which normal points INSIDE
    # Point = Midpoint + small_step * Normal
    test_p1 = Point(midpoint[0] - dy * 0.0001, midpoint[1] + dx * 0.0001)

    bearing = 0.0

    if parcel_poly.contains(test_p1) or parcel_poly.distance(test_p1) < 1e-8:
        # N1 is inward
        # Bearing of N1 (-dy, dx)
        # atan2(x, y) order: atan2(dx, dy) -> standard math atan2(y, x)
        # Compass bearing: 0 is North (y axis), 90 East (x axis).
        # Math angle: 0 is East, 90 is North.
        # Bearing = (90 - MathDegree) % 360 ?
        # Or just use atan2(dx, dy) converted.
        angle = math.degrees(math.atan2(dx, -dy))
    else:
        # N2 is inward (dy, -dx)
        angle = math.degrees(math.atan2(-dx, dy))

    # Standardize to 0-360 compass
    # Math: atan2(y, x).
    # Compass: 0 at North.
    # angle above was atan2(x_component, y_component) which gives angle from Y-axis (North) if (x,y)
    # Wait, let's verify.
    # Vector (0, 1) [North]. atan2(0, 1) = 0. Correct.
    # Vector (1, 0) [East]. atan2(1, 0) = 90. Correct.
    # Vector (0, -1) [South]. atan2(0, -1) = 180. Correct.
    # Vector (-1, 0) [West]. atan2(-1, 0) = -90 -> 270. Correct.

    bearing = angle % 360

    desc = "North"
    if 45 <= bearing < 135:
        desc = "East"
    if 135 <= bearing < 225:
        desc = "South"
    if 225 <= bearing < 315:
        desc = "West"

    # Refine
    if 337.5 <= bearing or bearing < 22.5:
        desc = "North"
    elif 22.5 <= bearing < 67.5:
        desc = "North-East"
    elif 67.5 <= bearing < 112.5:
        desc = "East"
    elif 112.5 <= bearing < 157.5:
        desc = "South-East"
    elif 157.5 <= bearing < 202.5:
        desc = "South"
    elif 202.5 <= bearing < 247.5:
        desc = "South-West"
    elif 247.5 <= bearing < 292.5:
        desc = "West"
    elif 292.5 <= bearing < 337.5:
        desc = "North-West"

    return bearing, desc
