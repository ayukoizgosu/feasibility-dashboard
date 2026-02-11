import os
import zipfile
from pathlib import Path

import requests
from rich.console import Console

console = Console()

# Official 2025 School Zones URL
SCHOOL_ZONES_URL = "https://www.education.vic.gov.au/Documents/about/research/datavic/dv397_DataVic_School_Zones_2025.zip"

DATA_DIR = Path("data")
ZONES_DIR = DATA_DIR / "school_zones"
ZIP_FILE = DATA_DIR / "school_zones_2025.zip"


def setup_school_zones():
    console.print("[bold blue]Setting up Victorian School Zones...[/bold blue]")

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    # 1. Download
    if not ZIP_FILE.exists():
        console.print(f"Downloading from {SCHOOL_ZONES_URL}...")
        try:
            resp = requests.get(SCHOOL_ZONES_URL, stream=True)
            resp.raise_for_status()

            with open(ZIP_FILE, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            console.print("[green]Download complete.[/green]")
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            return

    # 2. Extract
    if not ZONES_DIR.exists():
        console.print(f"Extracting to {ZONES_DIR}...")
        try:
            with zipfile.ZipFile(ZIP_FILE, "r") as zip_ref:
                zip_ref.extractall(ZONES_DIR)
            console.print("[green]Extraction complete.[/green]")
        except Exception as e:
            console.print(f"[red]Extraction failed: {e}[/red]")
            return

    # 3. List files
    console.print("\nFound spatial files:")
    shapefiles = list(ZONES_DIR.rglob("*.shp"))
    for shp in shapefiles:
        console.print(f" - {shp.name}")

    console.print("\n[yellow]Now run the loader:[/yellow]")
    console.print("python -m scanner.ingest.load_schools")


if __name__ == "__main__":
    setup_school_zones()
    setup_school_zones()
