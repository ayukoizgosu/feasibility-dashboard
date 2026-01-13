"""Yarra Valley Water WFS integration for sewerage verification.

This module provides functions to check sewerage availability using
the YVW public WFS endpoint.

WFS Endpoint: https://webmap.yvw.com.au/YVWassets/service.svc/get
Available Layers:
  - SEWERPIPES: Main sewer pipes (reticulated network)
  - SEWERBRANCHES: Connections from main to property boundaries
  - SEWERSTRUCTURES: Maintenance holes, pits, nodes
  - SEWERFITTINGS: Bends, junctions, valves
  - SEWERACCESSPOINTS: Clean-outs and inspection points

Note: WFS may timeout on some networks. Use browser-based check as fallback.
"""

from dataclasses import dataclass

import requests
from rich.console import Console

console = Console()

# YVW WFS Configuration
YVW_WFS_URL = "https://webmap.yvw.com.au/YVWassets/service.svc/get"
YVW_SEWER_LAYERS = [
    "SEWERPIPES",
    "SEWERBRANCHES",
]

# Search radius in degrees (approx 100m)
SEARCH_DISTANCE_DEG = 0.001


@dataclass
class YVWSewerCheck:
    """Result of YVW WFS sewerage check."""

    sewer_nearby: bool | None  # None = check failed
    pipe_count: int
    branch_count: int
    nearest_distance_m: float | None
    note: str
    check_succeeded: bool


def check_yvw_sewerage(
    lat: float,
    lon: float,
    timeout_seconds: int = 15,
) -> YVWSewerCheck:
    """Check YVW WFS for sewer infrastructure near a property.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        timeout_seconds: Request timeout

    Returns:
        YVWSewerCheck with results
    """
    pipe_count = 0
    branch_count = 0

    # Create BBOX around property (approximately 200m x 200m)
    min_lat = lat - SEARCH_DISTANCE_DEG
    max_lat = lat + SEARCH_DISTANCE_DEG
    min_lon = lon - SEARCH_DISTANCE_DEG
    max_lon = lon + SEARCH_DISTANCE_DEG

    for layer_name in YVW_SEWER_LAYERS:
        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": layer_name,
            "outputFormat": "GML2",
            "srsName": "EPSG:4326",
            "BBOX": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "maxFeatures": "50",
        }

        try:
            resp = requests.get(
                YVW_WFS_URL,
                params=params,
                timeout=timeout_seconds,
            )

            if resp.status_code == 200:
                content = resp.text
                # Count feature members in GML
                count = content.count("<gml:featureMember")
                if layer_name == "SEWERPIPES":
                    pipe_count = count
                elif layer_name == "SEWERBRANCHES":
                    branch_count = count

        except requests.Timeout:
            console.print(f"[yellow]YVW WFS timeout for {layer_name}[/yellow]")
            return YVWSewerCheck(
                sewer_nearby=None,
                pipe_count=0,
                branch_count=0,
                nearest_distance_m=None,
                note="WFS request timed out. Use manual check or Asset Map.",
                check_succeeded=False,
            )
        except Exception as e:
            console.print(f"[red]YVW WFS error: {e}[/red]")
            return YVWSewerCheck(
                sewer_nearby=None,
                pipe_count=0,
                branch_count=0,
                nearest_distance_m=None,
                note=f"WFS error: {e}",
                check_succeeded=False,
            )

    # Determine sewerage availability
    total_features = pipe_count + branch_count

    if total_features > 0:
        return YVWSewerCheck(
            sewer_nearby=True,
            pipe_count=pipe_count,
            branch_count=branch_count,
            nearest_distance_m=None,  # Would need geometry parsing
            note=f"Found {pipe_count} sewer pipes and {branch_count} branches within 100m",
            check_succeeded=True,
        )
    else:
        return YVWSewerCheck(
            sewer_nearby=False,
            pipe_count=0,
            branch_count=0,
            nearest_distance_m=None,
            note="No sewer infrastructure found within 100m",
            check_succeeded=True,
        )


def get_yvw_asset_map_url(lat: float, lon: float) -> str:
    """Generate URL to YVW Asset Map centered on property.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        URL to open in browser for manual check
    """
    # The YVW Asset Map uses a different coordinate system internally
    # but we can link to the general map
    return f"https://webmap.yvw.com.au/yvw_ext/?lat={lat}&lon={lon}&zoom=17"


if __name__ == "__main__":
    # Test with 2 Quamby Place, Donvale
    result = check_yvw_sewerage(lat=-37.7849813, lon=145.1825641)

    console.print("\n[bold]YVW Sewerage Check Result:[/bold]")
    console.print(f"  Check succeeded: {result.check_succeeded}")
    console.print(f"  Sewer nearby: {result.sewer_nearby}")
    console.print(f"  Pipes found: {result.pipe_count}")
    console.print(f"  Branches found: {result.branch_count}")
    console.print(f"  Note: {result.note}")

    # Also print Asset Map URL for manual verification
    url = get_yvw_asset_map_url(-37.7849813, 145.1825641)
    console.print(f"\n[blue]Manual check: {url}[/blue]")
    console.print(f"\n[blue]Manual check: {url}[/blue]")
