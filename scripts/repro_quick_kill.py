import logging

from rich.console import Console

from scanner.constraints.quick_kill import evaluate_quick_kill
from scanner.spatial.gis_clients import check_property_easements

console = Console()
logging.basicConfig(level=logging.DEBUG)

# 24 Dryden St, Doncaster East
LAT = -37.7863394
LON = 145.1587491


def debug_quick_kill():
    console.print(f"[bold]Debugging Quick Kill for {LAT}, {LON}[/bold]")

    # 1. Test Easements directly (Suspect)
    console.print("\n--- Testing Easements ---")
    try:
        has_blockers, has_any, easements = check_property_easements(LAT, LON)
        console.print(f"Result: {easements}")
    except Exception as e:
        console.print(f"[red]Easement Error: {e}[/red]")

    # 2. Test BPA directly
    console.print("\n--- Testing BPA (via project code) ---")
    try:
        from scanner.spatial.data_vic_checks import check_bushfire_prone_area

        is_bpa, bpa_info = check_bushfire_prone_area(LAT, LON)
        console.print(f"Result: {is_bpa}")
        if bpa_info:
            console.print(f"BPA Info: {bpa_info}")
    except Exception as e:
        console.print(f"[red]BPA Error: {e}[/red]")

    # 3. Test GA Infrastructure directly
    console.print("\n--- Testing GA Infrastructure (via project code) ---")
    try:
        from scanner.spatial.ga_infrastructure import (
            check_power_station_proximity,
            check_substation_proximity,
        )

        is_sub, sub_dist, sub_info = check_substation_proximity(
            LAT, LON, radius_m=50000
        )  # Large radius to find something
        console.print(f"Substation: Found={is_sub}, Dist={sub_dist}m")
        if sub_info:
            console.print(f"Sub Info: {sub_info}")

        is_ps, ps_dist, ps_info = check_power_station_proximity(
            LAT, LON, radius_m=50000
        )
        console.print(f"PowerStation: Found={is_ps}, Dist={ps_dist}m")
        if ps_info:
            console.print(f"PS Info: {ps_info}")

    except Exception as e:
        console.print(f"[red]GA Error: {e}[/red]")


if __name__ == "__main__":
    debug_quick_kill()

if __name__ == "__main__":
    debug_quick_kill()
