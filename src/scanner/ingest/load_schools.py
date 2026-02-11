import json
from pathlib import Path

import geopandas as gpd
from rich.console import Console
from shapely.geometry import shape

from scanner.db import get_session, init_db
from scanner.models import CachedSchoolZone

console = Console()
DATA_DIR = Path("data")
ZONES_DIR = DATA_DIR / "school_zones"


def load_schools():
    console.print("[bold blue]Loading Victorian School Zones...[/bold blue]")

    if not ZONES_DIR.exists():
        console.print(f"[red]Directory not found: {ZONES_DIR}[/red]")
        return

    init_db()

    # 1. Primary Schools
    primary_file = ZONES_DIR / "Primary_Integrated_2025.geojson"
    if primary_file.exists():
        load_geojson(primary_file, "Primary")

    # 2. Secondary Schools (Year 7 intake)
    secondary_file = ZONES_DIR / "Secondary_Integrated_Year7_2025.geojson"
    if secondary_file.exists():
        load_geojson(secondary_file, "Secondary")


def load_geojson(filepath: Path, school_type_label: str):
    console.print(f"Reading {filepath.name}...")
    try:
        gdf = gpd.read_file(filepath)
    except Exception as e:
        console.print(f"[red]Failed to read {filepath}: {e}[/red]")
        return

    console.print(f"  Found {len(gdf)} zones. converting to WGS84 if needed...")

    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    zones_to_add = []

    with get_session() as session:
        # Check existing count to see if we need to skip
        existing_count = (
            session.query(CachedSchoolZone)
            .filter_by(school_type=school_type_label, year=2025)
            .count()
        )
        console.print(f"  Existing {school_type_label} zones in DB: {existing_count}")

        # If we have relatively few, assume we reload. If we have thousands, maybe skip?
        # For now, let's just clear and reload to be safe and simple, or upsert.
        # Clearing is faster for a full reload.
        if existing_count > 0 and existing_count < len(gdf) * 0.9:
            console.print(
                "[yellow]Partial data detected. Clearing this type/year to reload...[/yellow]"
            )
            session.query(CachedSchoolZone).filter_by(
                school_type=school_type_label, year=2025
            ).delete()
            session.commit()
        elif existing_count >= len(gdf):
            console.print(
                f"[green]Data for {school_type_label} seems complete ({existing_count} records). Skipping.[/green]"
            )
            return

        # Track seen keys to avoid in-memory duplicates causing DB constraint errors
        seen_keys = set()

        console.print("  Processing features...")
        count = 0
        for idx, row in gdf.iterrows():
            try:
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue

                school_name = row.get("School_Name")
                if not school_name:
                    continue

                boundary_year = int(row.get("Boundary_Year", 2025))

                # Check for duplicates
                key = (school_name, boundary_year, school_type_label)
                if key in seen_keys:
                    # console.print(f"[dim]  Skipping duplicate: {school_name}[/dim]")
                    continue
                seen_keys.add(key)

                # Create object
                zone = CachedSchoolZone(
                    school_name=school_name,
                    school_type=school_type_label,
                    year=boundary_year,
                    geom_wkt=geom.wkt,
                    min_lat=geom.bounds[1],
                    max_lat=geom.bounds[3],
                    min_lon=geom.bounds[0],
                    max_lon=geom.bounds[2],
                    attributes={k: str(v) for k, v in row.items() if k != "geometry"},
                )
                zones_to_add.append(zone)
                count += 1

                if len(zones_to_add) >= 500:
                    session.bulk_save_objects(zones_to_add)
                    session.commit()
                    zones_to_add = []
                    console.print(f"  Loaded {count}...", end="\r")

            except Exception as e:
                console.print(f"[yellow]Error prepairing row {idx}: {e}[/yellow]")

        if zones_to_add:
            session.bulk_save_objects(zones_to_add)
            session.commit()

    console.print(
        f"[green]Successfully loaded {count} {school_type_label} zones.[/green]"
    )


if __name__ == "__main__":
    load_schools()
