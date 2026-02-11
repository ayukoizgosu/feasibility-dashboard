"""
Data.Vic WFS Checks Module
Queries the Victorian Government Data.Vic WFS for property constraints:
- Bushfire Prone Areas (BPA)
- EPA Priority Sites (Contamination)
- Landfills
- Flood Overlays
"""

import requests
from rich.console import Console

from scanner.spatial.gis_clients import haversine_distance

console = Console()

WFS_URL = "https://opendata.maps.vic.gov.au/geoserver/wfs"
TIMEOUT_SEC = 20


def _get_min_distance_to_feature(lat: float, lon: float, feature: dict) -> float:
    """Calculate minimum distance from point to feature geometry."""
    geom = feature.get("geometry", {})
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])

    min_dist = float("inf")

    if not coords:
        return min_dist

    if gtype == "Point":
        # coords is [lon, lat]
        dist = haversine_distance(lat, lon, coords[1], coords[0])
        min_dist = dist

    elif gtype == "MultiPolygon":
        # Simplified: check distance to first point of each polygon ring
        # For exact distance to polygon edge, we'd need Shapely (too heavy? maybe)
        # Using vertex proximity is a reasonable approximation for "nearby" checks
        for poly in coords:
            for ring in poly:
                for pt in ring:
                    dist = haversine_distance(lat, lon, pt[1], pt[0])
                    if dist < min_dist:
                        min_dist = dist

    elif gtype == "Polygon":
        for ring in coords:
            for pt in ring:
                dist = haversine_distance(lat, lon, pt[1], pt[0])
                if dist < min_dist:
                    min_dist = dist

    return min_dist


def check_bushfire_prone_area(lat: float, lon: float) -> tuple[bool, dict | None]:
    """Check if location is in a Designated Bushfire Prone Area (BPA)."""
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:bushfire_prone_area",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": f"INTERSECTS(geom, POINT({lat} {lon}))",
        "maxFeatures": 1,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            if features:
                # Inside BPA (distance 0)
                props = features[0].get("properties", {})
                return True, props
        return False, None
    except Exception as e:
        console.print(f"[yellow]  ! BPA check warning: {e}[/yellow]")
        return False, None


def check_epa_priority_sites(lat: float, lon: float, radius_m: int = 500) -> list[dict]:
    """Check for EPA Priority Sites (contamination) within radius."""
    # Approximate degree radius (1 deg ~= 111km)
    radius_deg = radius_m / 111000.0

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:psr_point",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": f"DWITHIN(geom, POINT({lat} {lon}), {radius_deg}, meters)",
        "count": 10,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            results = []
            for f in features:
                # Add calculated distance
                dist = _get_min_distance_to_feature(lat, lon, f)
                f["properties"]["distance_m"] = dist
                results.append(f)
            return results
        return []
    except Exception as e:
        console.print(f"[yellow]  ! EPA PSR check warning: {e}[/yellow]")
        return []


def check_enviro_audit_sites(lat: float, lon: float, radius_m: int = 500) -> list[dict]:
    """Check for Environmental Audit Overlay sites (often former industrial/waste)."""
    radius_deg = radius_m / 111000.0

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:enviro_audit_point",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": f"DWITHIN(geom, POINT({lon} {lat}), {radius_deg}, meters)",
        "count": 10,
    }

    try:
        resp = requests.get(WFS_URL, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            results = []
            for f in features:
                dist = _get_min_distance_to_feature(lat, lon, f)
                f["properties"]["distance_m"] = dist
                results.append(f)
            return results
        return []
    except Exception as e:
        console.print(f"[yellow]  ! Enviro Audit check warning: {e}[/yellow]")
        return []
