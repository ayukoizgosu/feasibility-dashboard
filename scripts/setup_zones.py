import sys
import webbrowser
from pathlib import Path

from rich.console import Console

console = Console()

DATA_DIR = Path("data")
FILE_NAME = "planning_zones.gpkg"
FILE_PATH = DATA_DIR / FILE_NAME
URL = "https://discover.data.vic.gov.au/dataset/vicmap-planning"


def check_and_guide():
    if not DATA_DIR.exists():
        DATA_DIR.mkdir()

    if FILE_PATH.exists():
        console.print(f"[green]✓ Found {FILE_NAME}[/green]")
        console.print("[bold]Starting data load...[/bold]")

        # Run the loader
        import scanner.spatial.load as loader

        loader.load_planning_zones(FILE_PATH)
        return

    console.print(f"[yellow]⚠ File {FILE_NAME} not found in data/[/yellow]")
    console.print(f"Please download the 'Vicmap Planning Zones' GeoPackage from:")
    console.print(f"[blue underline]{URL}[/blue underline]")
    console.print(f"\nSave it as: [bold]{FILE_PATH.absolute()}[/bold]")

    if console.input("Open download page now? (y/n): ").lower().strip() == "y":
        webbrowser.open(URL)
        console.print("Opening browser...")

    console.print(
        "\n[bold]Once downloaded, run this script again to load the data.[/bold]"
    )


if __name__ == "__main__":
    check_and_guide()
    check_and_guide()
