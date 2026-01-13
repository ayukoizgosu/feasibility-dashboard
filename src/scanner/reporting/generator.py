"""Generate reports for finding results."""

from datetime import datetime
from pathlib import Path

from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.models import FeasibilityRun, Site, SiteConstraint

console = Console()


def generate_deal_sheet(output_dir: str = "reports") -> None:
    """Generate a breakdown of the best opportunities."""
    config = get_config()
    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True, parents=True)

    filename = out_path / f"deal_sheet_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    with get_session() as session:
        # Fetch top feasible sites
        # Join FeasibilityRun to get scores
        results = (
            session.query(FeasibilityRun)
            .join(Site)
            .filter(FeasibilityRun.score > 0)
            .order_by(FeasibilityRun.score.desc())
            .limit(config.output.top_n)
            .all()
        )

        if not results:
            console.print("[yellow]No feasible deals found to report.[/yellow]")
            return

        with open(filename, "w", encoding="utf-8") as f:
            f.write("# Property Deal Sheet\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"**Top Candidates:** {len(results)}\n\n")
            f.write("---\n\n")

            for run in results:
                site = run.site
                constraints = (
                    session.query(SiteConstraint).filter_by(site_id=site.id).all()
                )

                # Header
                f.write(f"## {site.address_norm}\n")
                f.write(
                    f"[Google Maps](https://www.google.com/maps/search/?api=1&query={site.lat},{site.lon})\n\n"
                )

                # Key Metrics Table
                f.write("| Metric | Value |\n")
                f.write("| :--- | :--- |\n")
                f.write(
                    f"| **Land Area** | {run.assumptions.get('land_area_m2', 0):.0f} sqm |\n"
                )
                f.write(f"| **Zone** | {run.assumptions.get('zone', 'Unknown')} |\n")
                f.write(
                    f"| **Strategy** | {run.margin_base * 100:.1f}% Margin ({'DualOcc' if run.profit_base > 0 else 'Single'}) |\n"
                )  # Simplification
                f.write(f"| **Purchase Price** | ${run.land_cost/1_000_000:.2f}M |\n")
                f.write(f"| **Est. Profit** | ${run.profit_base/1_000_000:.2f}M |\n")
                f.write(f"| **Score** | {run.score:.2f} |\n\n")

                # Feasibility Details
                f.write("### Financial Feasibility\n")
                f.write(f"- **GDV**: ${run.revenue_base/1_000_000:.2f}M\n")
                f.write(f"- **TDC**: ${run.total_cost_base/1_000_000:.2f}M\n")
                f.write(
                    f"- **Yield**: {run.dwellings_base} dwellings (Range: {run.dwellings_low}-{run.dwellings_high})\n"
                )

                # Constraints & Risks
                f.write("### Constraints & Risks\n")
                has_risks = False
                for c in constraints:
                    if c.severity >= 3:
                        icon = "🔴"  # Blocker/High Risk
                        has_risks = True
                    elif c.severity == 2:
                        icon = "🟠"  # Orange/Moderate
                        has_risks = True
                    elif c.severity == 1:
                        icon = "🟡"  # Low Risk
                    else:
                        icon = "info"  # Info

                    # Skip boring info constraints in summary unless meaningful
                    if c.severity > 0 or "zone" in c.constraint_type:
                        f.write(f"- {icon} **{c.code}**: {c.description}\n")
                        if c.details and "planning_constraints" in c.details:
                            for pc in c.details["planning_constraints"]:
                                f.write(f"  - ⚠️ {pc}\n")

                if not has_risks:
                    f.write("- ✅ Clean site (No major overlays detected)\n")

                f.write("\n---\n\n")

    console.print(f"[green]Report generated: {filename}[/green]")
