"""Resolve parcels for geocoded sites."""

from typing import Any
import math

from shapely import wkt, Point
from shapely.ops import nearest_points
from rich.console import Console

from scanner.models import Site, VicParcel
from scanner.db import get_session

console = Console()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters."""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def resolve_parcels(tolerance_m: float = 50.0) -> tuple[int, int]:
    """Match sites to cadastre parcels.
    
    Args:
        tolerance_m: Maximum distance to search for nearest parcel (meters)
    
    Returns:
        (matched_count, unmatched_count)
    """
    matched = 0
    unmatched = 0
    
    with get_session() as session:
        # Get geocoded sites without parcel
        sites = session.query(Site).filter(
            Site.lat.isnot(None),
            Site.lon.isnot(None),
            Site.parcel_id.is_(None),
            Site.geocode_status == "success"
        ).all()
        
        if not sites:
            console.print("[yellow]No sites to resolve parcels for[/yellow]")
            return 0, 0
        
        console.print(f"[blue]Resolving parcels for {len(sites)} sites...[/blue]")
        
        # Get all parcels for spatial search
        # In a real implementation, we'd use spatial indexing
        parcels = session.query(VicParcel).all()
        
        if not parcels:
            console.print("[red]No parcels loaded. Run 'make load-spatial' first.[/red]")
            return 0, len(sites)
        
        console.print(f"  Searching against {len(parcels)} parcels")
        
        # Build simple spatial index by rough grid
        # Group parcels by rounded lat/lon for faster lookup
        parcel_grid: dict[tuple[int, int], list[VicParcel]] = {}
        for parcel in parcels:
            if parcel.centroid_lat and parcel.centroid_lon:
                key = (int(parcel.centroid_lat * 100), int(parcel.centroid_lon * 100))
                if key not in parcel_grid:
                    parcel_grid[key] = []
                parcel_grid[key].append(parcel)
        
        for i, site in enumerate(sites):
            # Find nearby parcels using grid
            site_key = (int(site.lat * 100), int(site.lon * 100))
            
            # Check surrounding grid cells
            nearby_parcels = []
            for dlat in range(-1, 2):
                for dlon in range(-1, 2):
                    key = (site_key[0] + dlat, site_key[1] + dlon)
                    if key in parcel_grid:
                        nearby_parcels.extend(parcel_grid[key])
            
            if not nearby_parcels:
                unmatched += 1
                continue
            
            # Find containing or nearest parcel
            site_point = Point(site.lon, site.lat)
            best_parcel = None
            best_distance = float("inf")
            
            for parcel in nearby_parcels:
                try:
                    parcel_geom = wkt.loads(parcel.geom_wkt)
                    
                    # Check containment first
                    if parcel_geom.contains(site_point):
                        best_parcel = parcel
                        best_distance = 0
                        break
                    
                    # Calculate distance to centroid as approximation
                    dist = haversine_distance(
                        site.lat, site.lon,
                        parcel.centroid_lat, parcel.centroid_lon
                    )
                    
                    if dist < best_distance:
                        best_distance = dist
                        best_parcel = parcel
                        
                except Exception:
                    continue
            
            if best_parcel and best_distance <= tolerance_m:
                site.parcel_id = best_parcel.parcel_id
                site.land_area_m2 = best_parcel.area_m2 or site.land_size_listed
                matched += 1
            else:
                unmatched += 1
            
            if (i + 1) % 100 == 0:
                console.print(f"  Progress: {i + 1}/{len(sites)}")
                session.commit()
    
    console.print(f"[green]Parcel resolution complete: {matched} matched, {unmatched} unmatched[/green]")
    return matched, unmatched


def run():
    """Entry point for parcel resolution."""
    resolve_parcels()


if __name__ == "__main__":
    run()
