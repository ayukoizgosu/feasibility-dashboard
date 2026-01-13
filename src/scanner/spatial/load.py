"""Load Victorian spatial data from GeoPackage files."""

from pathlib import Path
from typing import Any

import geopandas as gpd
from rich.console import Console
from shapely import wkt

from scanner.models import VicParcel, PlanningZone, PlanningOverlay
from scanner.db import get_session, init_db

console = Console()

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"


def load_parcels(filepath: Path | str | None = None, limit: int | None = None) -> int:
    """Load Victorian cadastre parcels from GeoPackage.
    
    Args:
        filepath: Path to GeoPackage file. Default: data/vicmap_property.gpkg
        limit: Optional limit on number of parcels to load (for testing)
    
    Returns:
        Number of parcels loaded
    """
    if filepath is None:
        filepath = DATA_DIR / "vicmap_property.gpkg"
    
    filepath = Path(filepath)
    if not filepath.exists():
        console.print(f"[red]Parcel file not found: {filepath}[/red]")
        console.print("[yellow]Download from: https://discover.data.vic.gov.au/dataset/vicmap-property-simplified-1-parcel-view[/yellow]")
        return 0
    
    console.print(f"[blue]Loading parcels from {filepath}...[/blue]")
    
    # Read GeoPackage
    gdf = gpd.read_file(filepath)
    
    if limit:
        gdf = gdf.head(limit)
    
    console.print(f"  Found {len(gdf)} parcels")
    
    # Convert to WGS84 if needed
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        console.print("  Converting to WGS84...")
        gdf = gdf.to_crs(epsg=4326)
    
    # Store in database
    count = 0
    with get_session() as session:
        for idx, row in gdf.iterrows():
            try:
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                
                # Get parcel ID (try common column names)
                parcel_id = None
                for col in ["PFI", "PARCEL_PFI", "parcel_id", "OBJECTID"]:
                    if col in row.index:
                        parcel_id = str(row[col])
                        break
                
                if not parcel_id:
                    parcel_id = f"parcel_{idx}"
                
                # Get centroid
                centroid = geom.centroid
                
                # Get area
                area = row.get("AREA_HA", 0) * 10000  # Convert hectares to m2
                if area == 0:
                    # Calculate from geometry (less accurate)
                    area = geom.area * 111320 * 111320  # Rough conversion for lat/lon
                
                # Build attributes
                attrs = {}
                for col in ["LGA_NAME", "LOCALITY", "POSTCODE", "LOT_NUMBER", "PLAN_NUMBER"]:
                    if col in row.index and row[col] is not None:
                        attrs[col] = str(row[col])
                
                parcel = VicParcel(
                    parcel_id=parcel_id,
                    geom_wkt=geom.wkt,
                    centroid_lat=centroid.y,
                    centroid_lon=centroid.x,
                    area_m2=area,
                    attributes=attrs
                )
                
                session.merge(parcel)
                count += 1
                
                if count % 10000 == 0:
                    console.print(f"  Loaded {count} parcels...")
                    session.commit()
                    
            except Exception as e:
                console.print(f"[yellow]Error loading parcel {idx}: {e}[/yellow]")
    
    console.print(f"[green]Loaded {count} parcels[/green]")
    return count


def load_planning_zones(filepath: Path | str | None = None) -> int:
    """Load Victorian planning zones from GeoPackage.
    
    Args:
        filepath: Path to GeoPackage file. Default: data/planning_zones.gpkg
    
    Returns:
        Number of zones loaded
    """
    if filepath is None:
        filepath = DATA_DIR / "planning_zones.gpkg"
    
    filepath = Path(filepath)
    if not filepath.exists():
        console.print(f"[red]Zones file not found: {filepath}[/red]")
        console.print("[yellow]Download from: https://discover.data.vic.gov.au/dataset/planning-scheme-zones[/yellow]")
        return 0
    
    console.print(f"[blue]Loading planning zones from {filepath}...[/blue]")
    
    gdf = gpd.read_file(filepath)
    console.print(f"  Found {len(gdf)} zones")
    
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    
    count = 0
    with get_session() as session:
        for idx, row in gdf.iterrows():
            try:
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                
                # Get zone code
                zone_code = None
                for col in ["ZONE_CODE", "ZONE", "zone_code"]:
                    if col in row.index:
                        zone_code = str(row[col])
                        break
                
                if not zone_code:
                    continue
                
                # Get LGA
                lga = None
                for col in ["LGA", "LGA_NAME", "SCHEME"]:
                    if col in row.index and row[col]:
                        lga = str(row[col])
                        break
                
                centroid = geom.centroid
                
                attrs = {k: str(v) for k, v in row.items() 
                        if k != "geometry" and v is not None}
                
                zone = PlanningZone(
                    zone_code=zone_code,
                    lga=lga,
                    geom_wkt=geom.wkt,
                    centroid_lat=centroid.y,
                    centroid_lon=centroid.x,
                    attributes=attrs
                )
                session.add(zone)
                count += 1
                
                if count % 5000 == 0:
                    console.print(f"  Loaded {count} zones...")
                    session.commit()
                    
            except Exception as e:
                console.print(f"[yellow]Error loading zone {idx}: {e}[/yellow]")
    
    console.print(f"[green]Loaded {count} zones[/green]")
    return count


def load_planning_overlays(filepath: Path | str | None = None) -> int:
    """Load Victorian planning overlays from GeoPackage.
    
    Args:
        filepath: Path to GeoPackage file. Default: data/planning_overlays.gpkg
    
    Returns:
        Number of overlays loaded
    """
    if filepath is None:
        filepath = DATA_DIR / "planning_overlays.gpkg"
    
    filepath = Path(filepath)
    if not filepath.exists():
        console.print(f"[red]Overlays file not found: {filepath}[/red]")
        console.print("[yellow]Download from: https://discover.data.vic.gov.au/dataset/planning-scheme-overlays[/yellow]")
        return 0
    
    console.print(f"[blue]Loading planning overlays from {filepath}...[/blue]")
    
    gdf = gpd.read_file(filepath)
    console.print(f"  Found {len(gdf)} overlays")
    
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    
    count = 0
    with get_session() as session:
        for idx, row in gdf.iterrows():
            try:
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                
                # Get overlay code
                overlay_code = None
                for col in ["OVERLAY", "OVERLAY_CODE", "overlay_code", "ZONE_CODE"]:
                    if col in row.index:
                        overlay_code = str(row[col])
                        break
                
                if not overlay_code:
                    continue
                
                # Extract base type (e.g., HO123 -> HO)
                overlay_type = "".join(c for c in overlay_code if not c.isdigit())
                
                # Get LGA
                lga = None
                for col in ["LGA", "LGA_NAME", "SCHEME"]:
                    if col in row.index and row[col]:
                        lga = str(row[col])
                        break
                
                centroid = geom.centroid
                
                attrs = {k: str(v) for k, v in row.items() 
                        if k != "geometry" and v is not None}
                
                overlay = PlanningOverlay(
                    overlay_code=overlay_code,
                    overlay_type=overlay_type,
                    lga=lga,
                    geom_wkt=geom.wkt,
                    centroid_lat=centroid.y,
                    centroid_lon=centroid.x,
                    attributes=attrs
                )
                session.add(overlay)
                count += 1
                
                if count % 5000 == 0:
                    console.print(f"  Loaded {count} overlays...")
                    session.commit()
                    
            except Exception as e:
                console.print(f"[yellow]Error loading overlay {idx}: {e}[/yellow]")
    
    console.print(f"[green]Loaded {count} overlays[/green]")
    return count


def run():
    """Load all spatial data."""
    console.print("[bold]Loading Victorian spatial data...[/bold]")
    
    init_db()
    
    parcels = load_parcels()
    zones = load_planning_zones()
    overlays = load_planning_overlays()
    
    console.print(f"\n[bold green]Spatial data loaded:[/bold green]")
    console.print(f"  Parcels: {parcels}")
    console.print(f"  Zones: {zones}")
    console.print(f"  Overlays: {overlays}")


if __name__ == "__main__":
    run()
