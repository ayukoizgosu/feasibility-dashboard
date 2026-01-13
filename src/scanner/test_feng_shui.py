from rich.console import Console
from shapely.wkt import loads

from scanner.constraints.quick_kill import evaluate_quick_kill
from scanner.db import get_session
from scanner.models import CachedFengShui

console = Console()


def test_feng_shui_rejection():
    with get_session() as session:
        # 1. Test PUZ1 (Reject)
        puz = session.query(CachedFengShui).filter_by(feature_type="PUZ1").first()
        if puz:
            geom = loads(puz.geom_wkt)
            lat, lon = geom.centroid.y, geom.centroid.x
            console.print(
                f"\n[blue]Testing PUZ1 (Substation) at {lat}, {lon}...[/blue]"
            )

            result = evaluate_quick_kill(lat, lon, blocker_overlay_types=[])
            if result.should_reject and any("PUZ1" in r for r in result.reasons):
                console.print("[green]PASS: PUZ1 Rejected correctly.[/green]")
                console.print(result.reasons)
            else:
                console.print("[red]FAIL: PUZ1 NOT Rejected.[/red]")
                console.print(result.reasons)
        else:
            console.print("[yellow]No PUZ1 in cache to test.[/yellow]")

        # 2. Test Water (Warning)
        water = session.query(CachedFengShui).filter_by(feature_type="WATER").first()
        if water:
            geom = loads(water.geom_wkt)
            # Find a point near boundary (centroid might be far if huge)
            # Use centroid for now (if small enough)
            lat, lon = geom.centroid.y, geom.centroid.x
            console.print(
                f"\n[blue]Testing WATER (Reservoir) at {lat}, {lon}...[/blue]"
            )

            result = evaluate_quick_kill(lat, lon, blocker_overlay_types=[])
            if any("Water" in w for w in result.warnings):
                console.print("[green]PASS: Water Warning found.[/green]")
                console.print(result.warnings)
            else:
                console.print("[red]FAIL: Water Warning NOT found.[/red]")
                console.print(result.warnings if result.warnings else "No warnings")
        else:
            console.print("[yellow]No WATER in cache to test.[/yellow]")


if __name__ == "__main__":
    test_feng_shui_rejection()
    test_feng_shui_rejection()
