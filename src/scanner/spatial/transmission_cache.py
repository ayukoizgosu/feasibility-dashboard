"""Load and cache transmission line data for fast proximity checks.

Downloads transmission line data from Geoscience Australia WFS and caches
it locally in the database for fast spatial queries.
"""

from datetime import datetime, timedelta
from typing import Any

from rich.console import Console
from shapely import wkt
from shapely.geometry import LineString, MultiLineString, shape

from scanner.db import get_session, init_db
from scanner.models import TransmissionLine
from scanner.spatial.gis_clients import (
    GA_ELECTRICITY_WFS,
    LAYER_TRANSMISSION_LINES,
    haversine_distance,
    query_wfs_features,
)

console = Console()

# Direct download URL for Geoscience Australia electricity infrastructure
GA_ELECTRICITY_CDN = "https://d28rz98at9flks.cloudfront.net/150022/150022_01_1.zip"


def load_transmission_lines_from_cdn() -> list[dict[str, Any]]:
    """Load transmission lines from Geoscience Australia CDN (faster than WFS).

    Downloads the national electricity infrastructure ZIP file and extracts
    transmission line features.

    Returns:
        List of transmission line feature dicts
    """
    import io
    import json
    import zipfile

    import requests

    console.print(
        "[blue]Downloading transmission lines from Geoscience Australia CDN...[/blue]"
    )
    console.print(f"  URL: {GA_ELECTRICITY_CDN}")

    try:
        response = requests.get(GA_ELECTRICITY_CDN, timeout=120)
        response.raise_for_status()

        console.print(f"  Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

        # Extract ZIP file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # Find the transmission lines GeoJSON file
            for filename in zf.namelist():
                console.print(f"  Found: {filename}")
                if "transmission" in filename.lower() or "line" in filename.lower():
                    if filename.endswith(".json") or filename.endswith(".geojson"):
                        console.print(f"  [green]Loading: {filename}[/green]")
                        with zf.open(filename) as f:
                            data = json.load(f)
                            if "features" in data:
                                console.print(
                                    f"  [green]Found {len(data['features'])} features[/green]"
                                )
                                return data["features"]

            # If no specific transmission file, try to load all JSON files
            for filename in zf.namelist():
                if filename.endswith(".json") or filename.endswith(".geojson"):
                    console.print(f"  [yellow]Trying: {filename}[/yellow]")
                    with zf.open(filename) as f:
                        data = json.load(f)
                        if "features" in data:
                            features = data["features"]
                            # Filter for transmission lines
                            line_features = [
                                f
                                for f in features
                                if f.get("geometry", {}).get("type")
                                in ("LineString", "MultiLineString")
                            ]
                            if line_features:
                                console.print(
                                    f"  [green]Found {len(line_features)} line features[/green]"
                                )
                                return line_features

        console.print("[red]No transmission line data found in ZIP[/red]")
        return []

    except Exception as e:
        console.print(f"[red]CDN download failed: {e}[/red]")
        return []


def load_transmission_lines_from_wfs(
    bbox: tuple[float, float, float, float] | None = None,
    max_features: int = 5000,
) -> list[dict[str, Any]]:
    """Load transmission lines from Geoscience Australia WFS (fallback).

    Args:
        bbox: Optional bounding box (min_lon, min_lat, max_lon, max_lat).
              Defaults to Victoria bounding box.
        max_features: Maximum features to fetch

    Returns:
        List of transmission line feature dicts
    """
    if bbox is None:
        # Victoria bounding box (approximate)
        bbox = (140.9, -39.2, 150.0, -33.9)

    console.print(
        "[blue]Fetching transmission lines from Geoscience Australia WFS...[/blue]"
    )
    console.print(f"  Bbox: {bbox}")
    console.print(f"  Max features: {max_features}")

    features = query_wfs_features(
        GA_ELECTRICITY_WFS,
        LAYER_TRANSMISSION_LINES,
        bbox,
        max_features=max_features,
        timeout=120,  # Long timeout for full state download
    )

    console.print(
        f"  [green]Fetched {len(features)} transmission line features[/green]"
    )
    return features


def load_transmission_lines() -> list[dict[str, Any]]:
    """Load transmission lines from best available source.

    Tries CDN first (faster), falls back to WFS if needed.

    Returns:
        List of transmission line feature dicts
    """
    # Try CDN first (faster and more reliable)
    features = load_transmission_lines_from_cdn()

    if not features:
        console.print("[yellow]CDN failed, trying WFS fallback...[/yellow]")
        features = load_transmission_lines_from_wfs()

    return features


def cache_transmission_lines(features: list[dict[str, Any]]) -> int:
    """Cache transmission line features in the database.

    Args:
        features: List of GeoJSON feature dicts from WFS

    Returns:
        Number of lines cached
    """
    count = 0
    skipped_low_voltage = 0

    with get_session() as session:
        for i, feature in enumerate(features):
            try:
                props = feature.get("properties", {})
                geom_data = feature.get("geometry")

                if not geom_data:
                    continue

                # Debug: print first feature's property keys
                if i == 0:
                    console.print(f"  [dim]Property keys: {list(props.keys())}[/dim]")

                # Convert GeoJSON geometry to WKT
                geom = shape(geom_data)

                # Get feature ID
                feature_id = (
                    props.get("OBJECTID")
                    or props.get("FID")
                    or props.get("objectid")
                    or str(count)
                )

                # Parse voltage - try many possible field names (case-insensitive)
                voltage_kv = 0
                for key in props.keys():
                    key_lower = key.lower()
                    if "voltage" in key_lower or "kv" in key_lower:
                        voltage_str = str(props.get(key) or "0")
                        try:
                            voltage_kv = int(
                                "".join(c for c in voltage_str if c.isdigit()) or "0"
                            )
                            if voltage_kv > 0:
                                if i == 0:
                                    console.print(
                                        f"  [dim]Voltage field: {key} = {voltage_kv}kV[/dim]"
                                    )
                                break
                        except ValueError:
                            pass

                # Skip non-high-voltage lines (< 66kV) but count them
                if voltage_kv < 66:
                    skipped_low_voltage += 1
                    continue

                # Calculate bounding box
                bounds = geom.bounds  # (minx, miny, maxx, maxy)

                line = TransmissionLine(
                    feature_id=str(feature_id),
                    voltage_kv=voltage_kv,
                    owner=props.get("OWNER")
                    or props.get("OPERATOR")
                    or props.get("NETWORK"),
                    name=props.get("NAME") or props.get("LINE_NAME"),
                    geom_wkt=geom.wkt,
                    min_lon=bounds[0],
                    min_lat=bounds[1],
                    max_lon=bounds[2],
                    max_lat=bounds[3],
                    attributes=props,
                    fetched_at=datetime.utcnow(),
                )

                # Use merge to handle duplicates
                session.merge(line)
                count += 1

                if count % 100 == 0:
                    console.print(f"  Cached {count} lines...")
                    session.commit()

            except Exception as e:
                console.print(f"[yellow]Error caching line: {e}[/yellow]")

        session.commit()

    console.print(
        f"[green]Cached {count} high-voltage (66kV+) transmission lines[/green]"
    )
    if skipped_low_voltage > 0:
        console.print(f"  [dim]Skipped {skipped_low_voltage} lower-voltage lines[/dim]")
    return count


def get_cached_lines_near(
    lat: float,
    lon: float,
    radius_m: float = 500,
) -> list[dict[str, Any]]:
    """Get cached transmission lines near a point.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        radius_m: Search radius in meters

    Returns:
        List of line info dicts with distance_m calculated
    """
    # Convert radius to approximate degrees for bbox filter
    lat_offset = radius_m / 111000
    lon_offset = radius_m / 80000  # Rough for Melbourne latitude

    min_lat = lat - lat_offset
    max_lat = lat + lat_offset
    min_lon = lon - lon_offset
    max_lon = lon + lon_offset

    lines = []

    with get_session() as session:
        # Query lines whose bbox intersects our search area
        query = session.query(TransmissionLine).filter(
            TransmissionLine.voltage_kv >= 66,
            TransmissionLine.max_lat >= min_lat,
            TransmissionLine.min_lat <= max_lat,
            TransmissionLine.max_lon >= min_lon,
            TransmissionLine.min_lon <= max_lon,
        )

        for line in query.all():
            try:
                # Calculate minimum distance to line geometry
                line_geom = wkt.loads(line.geom_wkt)

                # Get closest point distance (in degrees, convert to meters)
                min_dist = _calculate_geometry_distance(lat, lon, line_geom)

                if min_dist <= radius_m:
                    lines.append(
                        {
                            "feature_id": line.feature_id,
                            "voltage_kv": line.voltage_kv,
                            "owner": line.owner,
                            "name": line.name,
                            "distance_m": min_dist,
                        }
                    )
            except Exception as e:
                console.print(f"[yellow]Error processing cached line: {e}[/yellow]")

    return sorted(lines, key=lambda x: x["distance_m"])


def _calculate_geometry_distance(lat: float, lon: float, geom) -> float:
    """Calculate minimum distance from point to geometry in meters."""
    min_dist = float("inf")

    # Handle different geometry types
    if isinstance(geom, LineString):
        coords = list(geom.coords)
    elif isinstance(geom, MultiLineString):
        coords = []
        for line in geom.geoms:
            coords.extend(list(line.coords))
    else:
        return float("inf")

    for coord in coords:
        dist = haversine_distance(lat, lon, coord[1], coord[0])
        min_dist = min(min_dist, dist)

    return min_dist


def check_transmission_proximity_cached(
    lat: float,
    lon: float,
    threshold_m: float = 300,
) -> tuple[bool, float | None, dict | None]:
    """Check transmission line proximity using local cache.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        threshold_m: Distance threshold in meters

    Returns:
        (is_within_threshold, closest_distance_m, closest_line_info)
    """
    lines = get_cached_lines_near(lat, lon, threshold_m + 100)

    if not lines:
        return (False, None, None)

    closest = lines[0]  # Already sorted by distance
    closest_dist = closest.get("distance_m", float("inf"))

    return (closest_dist <= threshold_m, closest_dist, closest)


def ensure_transmission_cache(max_age_days: int = 30) -> bool:
    """Ensure transmission line cache is populated and fresh.

    Args:
        max_age_days: Maximum age of cache before refresh

    Returns:
        True if cache is ready, False if failed
    """
    with get_session() as session:
        # Check if we have any cached lines
        count = session.query(TransmissionLine).count()

        if count > 0:
            # Check age of oldest line
            oldest = (
                session.query(TransmissionLine)
                .order_by(TransmissionLine.fetched_at.asc())
                .first()
            )

            if oldest and oldest.fetched_at:
                age = datetime.utcnow() - oldest.fetched_at
                if age < timedelta(days=max_age_days):
                    console.print(
                        f"[green]Transmission cache OK: {count} lines, {age.days} days old[/green]"
                    )
                    return True

    # Need to refresh cache
    console.print("[yellow]Transmission cache needs refresh[/yellow]")
    try:
        features = load_transmission_lines()  # Tries CDN first, then WFS
        if features:
            cache_transmission_lines(features)
            return True
        else:
            console.print("[red]Failed to load transmission lines[/red]")
            return False
    except Exception as e:
        console.print(f"[red]Failed to refresh transmission cache: {e}[/red]")
        return False


def run():
    """Entry point for cache management."""
    init_db()

    console.print("[bold]Transmission Line Cache Manager[/bold]")
    console.print()

    # Try to ensure cache
    if ensure_transmission_cache():
        console.print("\n[green]✓ Cache is ready[/green]")

        # Test query
        test_lat, test_lon = -37.8, 145.1  # Eastern Melbourne
        lines = get_cached_lines_near(test_lat, test_lon, 5000)
        console.print(
            f"\nTest query at ({test_lat}, {test_lon}): {len(lines)} lines within 5km"
        )
        for line in lines[:3]:
            console.print(f"  - {line['voltage_kv']}kV at {line['distance_m']:.0f}m")
    else:
        console.print("\n[red]✗ Cache setup failed[/red]")


if __name__ == "__main__":
    run()
