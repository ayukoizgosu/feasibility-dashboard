"""
Geoscience Australia Infrastructure Checks
Queries GA WFS for:
- Substations (Transmission)
- Major Power Stations
"""

import xml.etree.ElementTree as ET

import requests
from rich.console import Console

from scanner.spatial.gis_clients import haversine_distance

console = Console()

# GA Electricity Infrastructure WFS
# Note: Use Foundation_Electricity_Infrastructure for Substations/Power Stations
GA_WFS_URL = "https://services.ga.gov.au/gis/services/Foundation_Electricity_Infrastructure/MapServer/WFSServer"
TIMEOUT_SEC = 20


def _parse_ga_gml(xml_text: str) -> list[dict]:
    """Parse features from GA WFS GML/XML response."""
    try:
        root = ET.fromstring(xml_text)
        features = []

        # Iterate over all elements to find features (namespace agnostic)
        for member in root.iter():
            if "featureMember" in member.tag or "member" in member.tag:
                features_in_member = []
                for child in member:
                    props = {}
                    coords = []
                    # Extract properties
                    for elem in child:
                        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem.text and elem.text.strip():
                            props[tag] = elem.text.strip()

                        # Extract coordinates (pos, posList, coordinates)
                        if "posList" in tag or "coordinates" in tag or "pos" in tag:
                            # This is rough heuristic for GML parsing
                            text = elem.text or ""
                            vals = text.strip().replace(",", " ").split()
                            try:
                                # Assuming lat lon or lon lat depending on srs... GA is usually Lat Lon in GML?
                                # WFS 1.1.0 default is strictly defined.
                                # Let's try to grab pairs.
                                pairs = []
                                for i in range(0, len(vals) - 1, 2):
                                    pairs.append([float(vals[i]), float(vals[i + 1])])
                                coords.extend(pairs)
                            except Exception:
                                pass

                        # Recursive search for posList in children (e.g. geometry property)
                        for sub in elem.iter():
                            if "posList" in sub.tag and sub.text:
                                vals = sub.text.strip().split()
                                try:
                                    # GML 3.1.1 usually Lat Long order for EPSG:4326
                                    pairs = []
                                    for i in range(0, len(vals) - 1, 2):
                                        pairs.append(
                                            [float(vals[i]), float(vals[i + 1])]
                                        )
                                    coords.extend(pairs)
                                except Exception:
                                    pass

                    feature = {
                        "properties": props,
                        "geometry": {"type": "Unknown", "coordinates": coords},
                    }
                    features_in_member.append(feature)
                features.extend(features_in_member)
        return features
    except Exception as e:
        console.print(f"[yellow]  ! GML parse error: {e}[/yellow]")
        return []


def _calc_dist(lat: float, lon: float, feature: dict) -> float:
    """Calculate min distance to GML feature coords."""
    coords = feature.get("geometry", {}).get("coordinates", [])
    if not coords:
        return float("inf")

    min_dist = float("inf")
    for pt in coords:
        # Check both Lat/Lon and Lon/Lat assumptions since GML SRS can be tricky
        # Usually GML 3 + EPSG:4326 is Lat Lon.
        # But we can check both against our target to be safe or just assume one.
        # Let's assume Lat Lon (pt[0]=lat, pt[1]=lon)
        dist1 = haversine_distance(lat, lon, pt[0], pt[1])
        min_dist = min(min_dist, dist1)

        # Check swapped (Lon Lat)
        dist2 = haversine_distance(lat, lon, pt[1], pt[0])
        min_dist = min(min_dist, dist2)

    return min_dist


def check_substation_proximity(
    lat: float, lon: float, radius_m: int = 200
) -> tuple[bool, float | None, dict | None]:
    """Check for transmission substations within radius."""
    # Convert buffer to degrees approx
    radius_deg = radius_m / 111000.0
    bbox = [lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg]

    # Use WFS 1.1.0 which GA supports reliably with GML
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "Foundation_Electricity_Infrastructure:Transmission_Substations",
        "srsName": "EPSG:4326",
        "bbox": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},EPSG:4326",
        "maxFeatures": "1",
    }

    try:
        resp = requests.get(GA_WFS_URL, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            features = _parse_ga_gml(resp.text)
            if features:
                dist = _calc_dist(lat, lon, features[0])
                # If calc fails or is weird, default to radius_m as failsafe
                final_dist = dist if dist != float("inf") else radius_m
                return True, final_dist, features[0]["properties"]
        return False, None, None
    except Exception as e:
        console.print(f"[yellow]  ! Substation check warning: {e}[/yellow]")
        return False, None, None


def check_power_station_proximity(
    lat: float, lon: float, radius_m: int = 500
) -> tuple[bool, float | None, dict | None]:
    """Check for major power stations within radius."""
    radius_deg = radius_m / 111000.0
    bbox = [lon - radius_deg, lat - radius_deg, lon + radius_deg, lat + radius_deg]

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "Foundation_Electricity_Infrastructure:Major_Power_Stations",
        "srsName": "EPSG:4326",
        "bbox": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},EPSG:4326",
        "maxFeatures": "1",
    }

    try:
        resp = requests.get(GA_WFS_URL, params=params, timeout=TIMEOUT_SEC)
        if resp.status_code == 200:
            features = _parse_ga_gml(resp.text)
            if features:
                dist = _calc_dist(lat, lon, features[0])
                final_dist = dist if dist != float("inf") else radius_m
                return True, final_dist, features[0]["properties"]
        return False, None, None
    except Exception as e:
        console.print(f"[yellow]  ! Power station check warning: {e}[/yellow]")
        return False, None, None
        return False, None, None
