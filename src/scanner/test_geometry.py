from rich.console import Console

from scanner.spatial.geometry import (
    calculate_frontage,
    calculate_orientation,
    calculate_slope_and_elevation,
    get_property_polygon,
)

console = Console()


def test_geometry_analysis():
    # 1 Lookover Road, Donvale
    lat = -37.7948523
    lon = 145.208641

    console.print(f"[blue]Analyzing 1 Lookover Road ({lat}, {lon})...[/blue]")

    # 1. Get Parcel
    console.print("Fetching Parcel Polygon...")
    poly = get_property_polygon(lat, lon)

    if not poly:
        console.print("[red]Failed to fetch parcel.[/red]")
        return

    console.print(
        f"[green]Got Parcel![/green] Area: {poly.area * 111111 * 111111:.0f} sqm (approx)"
    )

    # 2. Frontage
    console.print("Calculating Frontage...")
    frontage, details = calculate_frontage(poly)
    console.print(f"[bold]Frontage: {frontage:.1f}m[/bold]")
    for d in details:
        console.print(f"  - {d}")

    # 3. Slope
    console.print("Calculating Slope...")
    slope, elev, note = calculate_slope_and_elevation(poly)
    console.print(f"[bold]Slope: {slope:.1f}%[/bold]")
    console.print(f"Avg Elevation: {elev:.1f}m")
    console.print(f"Note: {note}")

    # 4. Orientation
    console.print("Calculating Orientation (Rear Facing)...")
    bearing, desc = calculate_orientation(poly)
    console.print(f"[bold]Rear Orientation: {bearing:.1f}° ({desc})[/bold]")


if __name__ == "__main__":
    test_geometry_analysis()
    test_geometry_analysis()
