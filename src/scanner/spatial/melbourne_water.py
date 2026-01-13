"""Melbourne Water infrastructure integration for sewer and water mains.

This module provides functions to query Melbourne Water's public ArcGIS
FeatureServer endpoints for sewer and water main locations.

Endpoints:
  - Sewerage Network Mains: Major sewer transfer mains
  - Water Supply Main Pipelines: Major water supply mains

Note: These are indicative/high-level locations for asset protection.
For detailed reticulated sewer, check with individual retailers (YVW, SEW, etc).
"""

import math
from dataclasses import dataclass
from typing import Any

import requests
from rich.console import Console

console = Console()

# Melbourne Water ArcGIS FeatureServer Endpoints
MW_SEWER_URL = (
    "https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/"
    "Sewerage_Network_Mains/FeatureServer/0/query"
)
MW_WATER_URL = (
    "https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/"
    "Water_Supply_Main_Pipelines/FeatureServer/0/query"
)

# Default search radius in meters
DEFAULT_SEARCH_RADIUS_M = 200


@dataclass
class MWInfrastructureResult:
    """Result of Melbourne Water infrastructure query."""

    found: bool
    count: int
    features: list[dict[str, Any]]
    nearest_distance_m: float | None
    note: str
    query_succeeded: bool


def _degrees_to_meters(degrees: float, lat: float) -> float:
    """Convert degrees to approximate meters at given latitude."""
    # 1 degree latitude ≈ 111km
    # 1 degree longitude = 111km * cos(lat)
    avg_m_per_deg = 111000 * math.cos(math.radians(lat))
    return degrees * avg_m_per_deg


def _meters_to_degrees(meters: float, lat: float) -> float:
    """Convert meters to approximate degrees at given latitude."""
    avg_m_per_deg = 111000 * math.cos(math.radians(lat))
    return meters / avg_m_per_deg


def query_mw_infrastructure(
    lat: float,
    lon: float,
    endpoint_url: str,
    radius_m: float = DEFAULT_SEARCH_RADIUS_M,
    timeout_seconds: int = 30,
) -> MWInfrastructureResult:
    """Query Melbourne Water infrastructure near a location.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        endpoint_url: ArcGIS FeatureServer query URL
        radius_m: Search radius in meters
        timeout_seconds: Request timeout

    Returns:
        MWInfrastructureResult with features found
    """
    # Convert radius to degrees
    buffer = _meters_to_degrees(radius_m, lat)

    # Create envelope geometry for spatial query
    params = {
        "where": "1=1",
        "geometry": f"{lon-buffer},{lat-buffer},{lon+buffer},{lat+buffer}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "geojson",
    }

    try:
        resp = requests.get(
            endpoint_url,
            params=params,
            timeout=timeout_seconds,
        )

        if resp.status_code != 200:
            return MWInfrastructureResult(
                found=False,
                count=0,
                features=[],
                nearest_distance_m=None,
                note=f"HTTP {resp.status_code}: {resp.text[:200]}",
                query_succeeded=False,
            )

        data = resp.json()

        # Check for ArcGIS error response
        if "error" in data:
            return MWInfrastructureResult(
                found=False,
                count=0,
                features=[],
                nearest_distance_m=None,
                note=f"ArcGIS error: {data['error'].get('message', 'Unknown')}",
                query_succeeded=False,
            )

        features = data.get("features", [])

        return MWInfrastructureResult(
            found=len(features) > 0,
            count=len(features),
            features=features,
            nearest_distance_m=None,  # Would need distance calculation
            note=f"Found {len(features)} features within {radius_m}m",
            query_succeeded=True,
        )

    except requests.Timeout:
        return MWInfrastructureResult(
            found=False,
            count=0,
            features=[],
            nearest_distance_m=None,
            note="Request timed out",
            query_succeeded=False,
        )
    except Exception as e:
        return MWInfrastructureResult(
            found=False,
            count=0,
            features=[],
            nearest_distance_m=None,
            note=f"Error: {e}",
            query_succeeded=False,
        )


def check_mw_sewer_mains(
    lat: float,
    lon: float,
    radius_m: float = DEFAULT_SEARCH_RADIUS_M,
) -> MWInfrastructureResult:
    """Check for Melbourne Water sewer mains near a location.

    These are major transfer/trunk mains, not reticulated sewerage.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        radius_m: Search radius in meters

    Returns:
        MWInfrastructureResult
    """
    return query_mw_infrastructure(lat, lon, MW_SEWER_URL, radius_m)


def check_mw_water_mains(
    lat: float,
    lon: float,
    radius_m: float = DEFAULT_SEARCH_RADIUS_M,
) -> MWInfrastructureResult:
    """Check for Melbourne Water water supply mains near a location.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        radius_m: Search radius in meters

    Returns:
        MWInfrastructureResult
    """
    return query_mw_infrastructure(lat, lon, MW_WATER_URL, radius_m)


@dataclass
class SewerAssessment:
    """Combined sewer availability assessment."""

    mw_mains_nearby: bool | None  # Melbourne Water trunk mains
    mw_mains_count: int
    likely_reticulated: bool | None  # Heuristic guess
    min_lot_size: int  # For LDRZ calculations
    note: str
    query_succeeded: bool


def assess_sewer_availability(
    lat: float,
    lon: float,
    suburb: str | None = None,
) -> SewerAssessment:
    """Assess sewer availability combining MW data and heuristics.

    Strategy:
    1. Query Melbourne Water for trunk sewer mains
    2. If MW mains nearby (< 500m), likely reticulated available
    3. Fall back to suburb-based heuristics if query fails

    Args:
        lat: Latitude
        lon: Longitude
        suburb: Suburb name for heuristic fallback

    Returns:
        SewerAssessment with combined analysis
    """
    # Query MW sewer mains (wider radius for trunk detection)
    mw_result = check_mw_sewer_mains(lat, lon, radius_m=500)

    if mw_result.query_succeeded:
        if mw_result.found:
            # MW trunk main nearby - good indicator of reticulated area
            return SewerAssessment(
                mw_mains_nearby=True,
                mw_mains_count=mw_result.count,
                likely_reticulated=True,
                min_lot_size=2000,  # Assume sewered for LDRZ
                note=f"MW sewer main within 500m ({mw_result.count} found). Likely sewered area.",
                query_succeeded=True,
            )
        else:
            # No MW mains - likely unsewered/rural area
            return SewerAssessment(
                mw_mains_nearby=False,
                mw_mains_count=0,
                likely_reticulated=False,
                min_lot_size=4000,  # Assume unsewered for LDRZ
                note="No MW sewer mains within 500m. Likely unsewered - verify with YVW.",
                query_succeeded=True,
            )

    # Query failed - fall back to heuristics
    return SewerAssessment(
        mw_mains_nearby=None,
        mw_mains_count=0,
        likely_reticulated=None,
        min_lot_size=4000,  # Conservative assumption
        note=f"MW query failed: {mw_result.note}. Verify sewerage manually.",
        query_succeeded=False,
    )


def print_sewer_assessment(assessment: SewerAssessment) -> None:
    """Print formatted sewer assessment to console."""
    console.print("\n[bold blue]═══ SEWER AVAILABILITY ═══[/bold blue]\n")

    if assessment.query_succeeded:
        if assessment.mw_mains_nearby:
            console.print("[green]✓ MW Sewer Mains Nearby[/green]")
            console.print(f"  Count: {assessment.mw_mains_count}")
        else:
            console.print("[yellow]✗ No MW Sewer Mains Within 500m[/yellow]")

        if assessment.likely_reticulated:
            console.print("[green]✓ Likely Reticulated Sewer Area[/green]")
            console.print(f"  → Min LDRZ lot size: {assessment.min_lot_size}sqm")
        else:
            console.print("[red]✗ Likely Unsewered[/red]")
            console.print(f"  → Min LDRZ lot size: {assessment.min_lot_size}sqm")
    else:
        console.print("[yellow]? Query Failed[/yellow]")
        console.print(f"  → Assuming min lot size: {assessment.min_lot_size}sqm")

    console.print(f"\n[dim]{assessment.note}[/dim]")


if __name__ == "__main__":
    # Test with 2 Quamby Place, Donvale
    lat, lon = -37.7849813, 145.1825641

    console.print("\n[bold]Testing Melbourne Water endpoints for:[/bold]")
    console.print(f"2 Quamby Place, Donvale ({lat}, {lon})\n")

    # Test sewer mains
    console.print("[bold]Sewer Mains Query:[/bold]")
    sewer = check_mw_sewer_mains(lat, lon)
    console.print(f"  Succeeded: {sewer.query_succeeded}")
    console.print(f"  Found: {sewer.found}")
    console.print(f"  Count: {sewer.count}")
    console.print(f"  Note: {sewer.note}")

    # Test water mains
    console.print("\n[bold]Water Mains Query:[/bold]")
    water = check_mw_water_mains(lat, lon)
    console.print(f"  Succeeded: {water.query_succeeded}")
    console.print(f"  Found: {water.found}")
    console.print(f"  Count: {water.count}")
    console.print(f"  Note: {water.note}")

    # Combined assessment
    console.print("\n")
    assessment = assess_sewer_availability(lat, lon, suburb="Donvale")
    print_sewer_assessment(assessment)
