"""GIS API clients for Victorian planning and infrastructure data.

Provides unified access to:
- Vicmap Planning WFS (zones, overlays, heritage)
- Geoscience Australia WFS (transmission lines)
- Victorian Heritage Database API
"""

import math
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from rich.console import Console
from urllib3.util.retry import Retry

console = Console()

# =============================================================================
# WFS ENDPOINTS
# =============================================================================

# Victorian Government Open Data WFS
VICMAP_WFS_BASE = "https://opendata.maps.vic.gov.au/geoserver/wfs"

# Geoscience Australia - National Electricity Infrastructure
GA_ELECTRICITY_WFS = "https://services.ga.gov.au/gis/services/National_Electricity_Infrastructure/MapServer/WFSServer"

# Layer names for Vicmap Planning (confirmed from Data.vic catalogue)
# Use open-data-platform namespace, not datavic
LAYER_PLANNING_OVERLAY = "open-data-platform:plan_overlay"
LAYER_PLANNING_ZONE = "open-data-platform:plan_zone"
LAYER_HERITAGE_REGISTER = "open-data-platform:heritage_register"
LAYER_EASEMENT = "open-data-platform:easement"  # Vicmap Property Easement Line (all)

# Layer name for GA electricity (transmission lines)
LAYER_TRANSMISSION_LINES = (
    "Electricity_Transmission_Lines"  # Simplified - GA WFS may not need full namespace
)


# =============================================================================
# HTTP SESSION WITH RETRY
# =============================================================================


def _get_session() -> requests.Session:
    """Create session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# =============================================================================
# COORDINATE UTILITIES
# =============================================================================


def _create_bbox_around_point(
    lat: float, lon: float, buffer_m: float
) -> tuple[float, float, float, float]:
    """Create bounding box around a point with buffer in meters.

    Returns (min_lon, min_lat, max_lon, max_lat) in WGS84.
    """
    # Rough conversion: 1 degree lat ≈ 111km, 1 degree lon ≈ 111km * cos(lat)
    lat_offset = buffer_m / 111000
    lon_offset = buffer_m / (111000 * math.cos(math.radians(lat)))

    return (
        lon - lon_offset,  # min_lon
        lat - lat_offset,  # min_lat
        lon + lon_offset,  # max_lon
        lat + lat_offset,  # max_lat
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate crow-fly distance between two points in meters."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


# =============================================================================
# WFS QUERY FUNCTIONS
# =============================================================================


def query_wfs_features(
    wfs_base: str,
    layer: str,
    bbox: tuple[float, float, float, float] | None = None,
    cql_filter: str | None = None,
    max_features: int = 100,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Query WFS for features within bounding box or via CQL.

    Args:
        wfs_base: Base URL of WFS service
        layer: Layer/typename to query
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84 (optional if cql used)
        cql_filter: CQL filter string (optional)
        max_features: Maximum features to return
        timeout: Request timeout in seconds

    Returns:
        List of feature dictionaries with 'geometry' and 'properties' keys
    """
    # Build WFS GetFeature request
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": layer,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "maxFeatures": str(max_features),
    }

    if bbox:
        # WFS 1.1.0 usually lon,lat
        params["bbox"] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

    if cql_filter:
        params["cql_filter"] = cql_filter

    session = _get_session()

    try:
        response = session.get(wfs_base, params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()

        if "features" in data:
            return data["features"]
        else:
            return []

    except requests.exceptions.RequestException as e:
        console.print(f"[red]WFS request failed: {e}[/red]")
        return []
    except ValueError as e:
        # Log response body for debugging JSON decode errors
        resp_text = (
            response.text[:500] if "response" in dir() and response else "No response"
        )
        console.print(f"[red]Failed to parse WFS JSON: {e}[/red]")
        console.print(f"[dim]Response body (first 500 chars): {resp_text}[/dim]")
        return []


# =============================================================================
# GA ELECTRICITY WFS SPECIFIC
# =============================================================================


def query_ga_wfs_features(
    bbox: tuple[float, float, float, float],
    layer: str = "Electricity_Transmission_Lines",
    max_features: int = 100,
    timeout: int = 45,
) -> list[dict[str, Any]]:
    """Query Geoscience Australia WFS using WFS 1.1.0 format.

    GA's ArcGIS-based WFS may not support WFS 2.0.0 or JSON output.
    This uses WFS 1.1.0 with GML3 and parses the XML response.
    """
    ga_wfs_base = "https://services.ga.gov.au/gis/services/National_Electricity_Infrastructure/MapServer/WFSServer"

    # WFS 1.1.0 style request
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": layer,
        "srsName": "EPSG:4326",
        "bbox": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},EPSG:4326",
        "maxFeatures": str(max_features),
    }

    session = _get_session()

    try:
        response = session.get(ga_wfs_base, params=params, timeout=timeout)
        response.raise_for_status()

        # Check if response is XML (GML) or JSON
        content_type = response.headers.get("Content-Type", "")

        if "json" in content_type.lower():
            data = response.json()
            return data.get("features", [])

        # Parse GML/XML response
        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)

        # Extract features from GML
        features = []

        # Find all feature members (try multiple namespace patterns)
        for member in root.iter():
            if "featureMember" in member.tag or "member" in member.tag:
                for child in member:
                    props = {}
                    coords = []
                    for elem in child:
                        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem.text and elem.text.strip():
                            props[tag] = elem.text.strip()
                        # Try to extract coordinates
                        for pos in elem.iter():
                            if "posList" in pos.tag and pos.text:
                                coord_vals = pos.text.strip().split()
                                try:
                                    coords = [
                                        [float(coord_vals[i + 1]), float(coord_vals[i])]
                                        for i in range(0, len(coord_vals) - 1, 2)
                                    ]
                                except (ValueError, IndexError):
                                    pass

                    if props:
                        feature = {
                            "properties": props,
                            "geometry": (
                                {"type": "LineString", "coordinates": coords}
                                if coords
                                else {}
                            ),
                        }
                        features.append(feature)

        console.print(f"[dim]GA WFS: Parsed {len(features)} features from GML[/dim]")
        return features

    except requests.exceptions.RequestException as e:
        console.print(f"[red]GA WFS request failed: {e}[/red]")
        return []
    except Exception as e:
        resp_text = (
            response.text[:500] if "response" in dir() and response else "No response"
        )
        console.print(f"[red]GA WFS parse error: {e}[/red]")
        console.print(f"[dim]Response (first 500 chars): {resp_text}[/dim]")
        return []


# =============================================================================
# PLANNING OVERLAY QUERIES
# =============================================================================


def get_overlays_at_point(
    lat: float,
    lon: float,
    buffer_m: float = 50,
) -> list[dict[str, Any]]:
    """Get planning overlays that intersect with a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        buffer_m: Buffer around point in meters

    Returns:
        List of overlay info dicts with keys: code, type, lga, etc.
    """
    # Overlays work with BBOX query
    bbox = _create_bbox_around_point(lat, lon, buffer_m)
    features = query_wfs_features(VICMAP_WFS_BASE, LAYER_PLANNING_OVERLAY, bbox=bbox)

    overlays = []
    for feature in features:
        props = feature.get("properties", {})

        # ... processing keys ...
        zone_code = (
            props.get("ZONE_CODE")
            or props.get("ZONE")
            or props.get("LABEL")
            or props.get("MAP_LAB")
            or props.get("zone_code")
            or props.get("zone")
            or props.get("label")
        )

        if zone_code:
            overlays.append(
                {
                    "code": zone_code,
                    "type": props.get("ZONE_DESC")
                    or props.get("TYPE")
                    or props.get("zone_desc")
                    or props.get("type"),
                    "lga": props.get("LGA_NAME") or props.get("lga_name"),
                    "properties": props,
                }
            )

    return overlays


def get_zones_at_point(
    lat: float,
    lon: float,
    buffer_m: float = 50,
) -> list[dict[str, Any]]:
    """Get planning zones that intersect with a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        buffer_m: Buffer around point in meters

    Returns:
        List of zone info dicts with keys: code, lga, etc.
    """
    # Use CQL INTERSECTS with geom column and LAT LON order (proven for this layer)
    cql = f"INTERSECTS(geom, POINT({lat} {lon}))"

    features = query_wfs_features(VICMAP_WFS_BASE, LAYER_PLANNING_ZONE, cql_filter=cql)

    zones = []
    for feature in features:
        props = feature.get("properties", {})

        zone_code = (
            props.get("ZONE_CODE")
            or props.get("ZONE")
            or props.get("LABEL")
            or props.get("zone_code")
            or props.get("zone")
            or props.get("label")
        )

        if zone_code:
            zones.append(
                {
                    "code": zone_code,
                    "lga": props.get("LGA")
                    or props.get("LGA_NAME")
                    or props.get("SCHEME")
                    or props.get("lga_name")
                    or props.get("scheme"),
                    "properties": props,
                }
            )

    return zones


# =============================================================================
# HERITAGE QUERIES
# =============================================================================


def get_heritage_at_point(
    lat: float,
    lon: float,
    buffer_m: float = 50,
) -> list[dict[str, Any]]:
    """Check Victorian Heritage Register listings near a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        buffer_m: Buffer around point in meters

    Returns:
        List of heritage items with keys: vhr_number, name, type, etc.
    """
    bbox = _create_bbox_around_point(lat, lon, buffer_m)
    features = query_wfs_features(VICMAP_WFS_BASE, LAYER_HERITAGE_REGISTER, bbox)

    heritage_items = []
    for feature in features:
        props = feature.get("properties", {})

        heritage_items.append(
            {
                "vhr_number": props.get("VHR_NUMBER")
                or props.get("VHR_NO")
                or props.get("VHR"),
                "name": props.get("NAME") or props.get("VHR_NAME"),
                "type": props.get("TYPE") or props.get("HERITAGE_STATUS"),
                "address": props.get("ADDRESS") or props.get("LOCATION"),
                "properties": props,
            }
        )

    return heritage_items


# =============================================================================
# TRANSMISSION LINE QUERIES
# =============================================================================


def get_transmission_lines_near(
    lat: float,
    lon: float,
    radius_m: float = 500,
) -> list[dict[str, Any]]:
    """Get electricity transmission lines within radius of a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        radius_m: Search radius in meters

    Returns:
        List of transmission line info with keys: voltage_kv, owner, distance_m, etc.
    """
    bbox = _create_bbox_around_point(lat, lon, radius_m)
    # Use GA-specific WFS 1.1.0 query (handles XML/GML response)
    features = query_ga_wfs_features(bbox, LAYER_TRANSMISSION_LINES, timeout=45)

    lines = []
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        # Calculate minimum distance from point to line
        min_distance = _calculate_min_distance_to_geometry(lat, lon, geom)

        # Parse voltage
        voltage_str = str(props.get("OPERATINGVOLTAGE") or props.get("VOLTAGE") or "0")
        try:
            voltage_kv = int("".join(c for c in voltage_str if c.isdigit()) or "0")
        except ValueError:
            voltage_kv = 0

        lines.append(
            {
                "voltage_kv": voltage_kv,
                "owner": props.get("OWNER")
                or props.get("OPERATOR")
                or props.get("NETWORK"),
                "name": props.get("NAME") or props.get("LINE_NAME"),
                "distance_m": min_distance,
                "properties": props,
            }
        )

    return lines


def _calculate_min_distance_to_geometry(
    lat: float,
    lon: float,
    geometry: dict,
) -> float:
    """Calculate minimum distance from point to GeoJSON geometry.

    Returns distance in meters.
    """
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates", [])

    if not coords:
        return float("inf")

    min_dist = float("inf")

    if geom_type == "Point":
        min_dist = haversine_distance(lat, lon, coords[1], coords[0])

    elif geom_type == "LineString":
        for coord in coords:
            if len(coord) >= 2:
                dist = haversine_distance(lat, lon, coord[1], coord[0])
                min_dist = min(min_dist, dist)

    elif geom_type == "MultiLineString":
        for line in coords:
            for coord in line:
                if len(coord) >= 2:
                    dist = haversine_distance(lat, lon, coord[1], coord[0])
                    min_dist = min(min_dist, dist)

    elif geom_type == "Polygon":
        # Check distance to polygon exterior ring
        if coords and coords[0]:
            for coord in coords[0]:
                if len(coord) >= 2:
                    dist = haversine_distance(lat, lon, coord[1], coord[0])
                    min_dist = min(min_dist, dist)

    elif geom_type == "MultiPolygon":
        for polygon in coords:
            if polygon and polygon[0]:
                for coord in polygon[0]:
                    if len(coord) >= 2:
                        dist = haversine_distance(lat, lon, coord[1], coord[0])
                        min_dist = min(min_dist, dist)

    return min_dist


# =============================================================================
# CONVENIENCE FUNCTION FOR QUICK-KILL
# =============================================================================


# Easement type classification for nuanced rejection
EASEMENT_BLOCKERS = {
    # HIGH SEVERITY - Reject (major infrastructure, can't build over)
    "drainage": 3,
    "sewer": 3,
    "sewerage": 3,
    "stormwater": 3,
    "electricity": 3,
    "power": 3,
    "powerline": 3,
    "gas": 3,
    "water main": 3,
    "watermain": 3,
    "high voltage": 3,
    "transmission": 3,
    "pipeline": 3,
    # MEDIUM SEVERITY - Warning (may restrict building envelope)
    "water": 2,
    "carriageway": 2,
    "right of way": 2,
    "row": 2,
    "access": 2,
    "road": 2,
    "telecommunications": 2,
    "telecom": 2,
    "nbn": 2,
    # LOW SEVERITY - Info only (minor, usually manageable)
    "fencing": 1,
    "fence": 1,
    "party wall": 1,
    "light": 1,
    "air": 1,
    "support": 1,
    "encroachment": 1,
}


def classify_easement(easement_props: dict) -> tuple[str, int, str]:
    """
    Classify easement by type and severity.

    Args:
        easement_props: Properties dict from WFS feature

    Returns:
        (easement_type, severity, description)
        severity: 0=unknown, 1=low, 2=medium, 3=high (blocker)
    """
    # Try common property field names for easement type
    type_fields = [
        "EASEMENT_TYPE",
        "EASEMENT_PURPOSE",
        "TYPE",
        "PURPOSE",
        "DESCRIPTION",
        "DESC",
        "LABEL",
        "NAME",
    ]

    easement_text = ""
    for field in type_fields:
        val = easement_props.get(field)
        if val:
            easement_text = str(val).lower()
            break

    if not easement_text:
        # Check all properties for keywords
        easement_text = " ".join(str(v).lower() for v in easement_props.values() if v)

    # Match against known types
    for keyword, severity in EASEMENT_BLOCKERS.items():
        if keyword in easement_text:
            if severity == 3:
                desc = f"Major infrastructure easement ({keyword})"
            elif severity == 2:
                desc = f"Access/utility easement ({keyword})"
            else:
                desc = f"Minor easement ({keyword})"
            return keyword, severity, desc

    # Unknown - treat as medium concern
    return "unknown", 2, f"Unclassified easement: {easement_text[:50]}"


def get_easements_near_point(
    lat: float,
    lon: float,
    buffer_m: float = 50,
) -> list[dict[str, Any]]:
    """Get Vicmap easements near a point with classification.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        buffer_m: Search buffer radius in meters

    Returns:
        List of easement features with type, severity, and description
    """
    bbox = _create_bbox_around_point(lat, lon, buffer_m)

    try:
        features = query_wfs_features(
            VICMAP_WFS_BASE,
            LAYER_EASEMENT,
            bbox,
            max_features=20,
            timeout=8,  # Slightly longer timeout
        )

        results = []
        for feat in features:
            props = feat.get("properties", {})
            easement_type, severity, desc = classify_easement(props)

            results.append(
                {
                    "feature_id": feat.get("id"),
                    "easement_type": easement_type,
                    "severity": severity,
                    "description": desc,
                    "properties": props,
                }
            )

        return results
    except Exception as e:
        console.print(f"[yellow]Easement WFS query failed: {e}[/yellow]")
        return []


def check_property_easements(
    lat: float, lon: float
) -> tuple[bool, bool, list[dict[str, Any]]]:
    """Check for easements on/near the property with severity classification.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        (has_blockers, has_any_easement, easements_found)
        - has_blockers: True if severity 3 (major infrastructure) easement found
        - has_any_easement: True if any easement found
        - easements_found: List of classified easements
    """
    # Use 30m buffer to catch easements on boundary of a typical block
    easements = get_easements_near_point(lat, lon, buffer_m=30)

    has_blockers = any(e.get("severity", 0) >= 3 for e in easements)
    has_any = len(easements) > 0

    return (has_blockers, has_any, easements)


def check_transmission_proximity(
    lat: float,
    lon: float,
    threshold_m: float = 300,
) -> tuple[bool, float | None, dict | None]:
    """Check if point is within threshold distance of high-voltage transmission lines.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        threshold_m: Distance threshold in meters

    Returns:
        (is_within_threshold, closest_distance_m, closest_line_info)
    """
    # Search slightly wider than threshold to catch lines
    lines = get_transmission_lines_near(lat, lon, threshold_m + 200)

    if not lines:
        return (False, None, None)

    # Filter to high voltage (66kV+) and find closest
    hv_lines = [line for line in lines if line.get("voltage_kv", 0) >= 66]

    if not hv_lines:
        return (False, None, None)

    closest = min(hv_lines, key=lambda x: x.get("distance_m", float("inf")))
    closest_dist = closest.get("distance_m", float("inf"))

    return (closest_dist <= threshold_m, closest_dist, closest)


def check_blocker_overlays(
    lat: float,
    lon: float,
    blocker_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Check for blocking planning overlays at a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        blocker_types: List of overlay types to check (default: HO, VHR, PAO, EAO, BMO)

    Returns:
        List of blocking overlays found
    """
    if blocker_types is None:
        blocker_types = ["HO", "VHR", "PAO", "EAO", "BMO"]

    overlays = get_overlays_at_point(lat, lon)

    blockers = []
    for overlay in overlays:
        overlay_type = overlay.get("type", "")
        if overlay_type in blocker_types:
            blockers.append(overlay)

    return blockers


def check_heritage_register(
    lat: float,
    lon: float,
) -> list[dict[str, Any]]:
    """Check Victorian Heritage Register for listings at point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84

    Returns:
        List of heritage register items found
    """
    return get_heritage_at_point(lat, lon)


# =============================================================================
# TESTING / DIAGNOSTICS
# =============================================================================


def test_wfs_connectivity() -> dict[str, bool]:
    """Test connectivity to all WFS endpoints.

    Returns:
        Dict mapping endpoint name to success status
    """
    results = {}

    # Test Vicmap WFS
    try:
        response = requests.get(
            VICMAP_WFS_BASE,
            params={"service": "WFS", "request": "GetCapabilities"},
            timeout=30,
        )
        results["vicmap_wfs"] = response.status_code == 200
    except Exception:
        results["vicmap_wfs"] = False

    # Test GA Electricity WFS
    try:
        response = requests.get(
            GA_ELECTRICITY_WFS,
            params={"service": "WFS", "request": "GetCapabilities"},
            timeout=30,
        )
        results["ga_electricity_wfs"] = response.status_code == 200
    except Exception:
        results["ga_electricity_wfs"] = False

    return results


if __name__ == "__main__":
    # Quick connectivity test
    console.print("[bold]Testing WFS connectivity...[/bold]")
    results = test_wfs_connectivity()
    for name, success in results.items():
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        console.print(f"  {status} {name}")

    # Test point query (Melbourne CBD)
    console.print("\n[bold]Testing point query (Melbourne CBD)...[/bold]")
    test_lat, test_lon = -37.8136, 144.9631

    zones = get_zones_at_point(test_lat, test_lon)
    console.print(f"  Zones found: {len(zones)}")
    for z in zones[:3]:
        console.print(f"    - {z.get('code')}")

    overlays = get_overlays_at_point(test_lat, test_lon)
    console.print(f"  Overlays found: {len(overlays)}")
    for o in overlays[:3]:
        console.print(f"    - {o.get('code')} ({o.get('type')})")
