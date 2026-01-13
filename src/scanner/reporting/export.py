"""Export reports for top sites."""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from scanner.config import get_config
from scanner.models import Site, SiteConstraint, FeasibilityRun
from scanner.db import get_session

console = Console()

# Reports directory
REPORTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "reports"


def export_top_sites(top_n: int = None) -> int:
    """Export top N sites to CSV and individual reports.
    
    Returns:
        Number of sites exported
    """
    config = get_config()
    top_n = top_n or config.output.top_n
    
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    with get_session() as session:
        # Get top sites by feasibility score
        top_runs = session.query(FeasibilityRun).order_by(
            FeasibilityRun.score.desc()
        ).limit(top_n).all()
        
        if not top_runs:
            console.print("[yellow]No feasibility runs found. Run 'make score' first.[/yellow]")
            return 0
        
        console.print(f"[blue]Exporting top {len(top_runs)} sites...[/blue]")
        
        # Export CSV summary
        csv_path = REPORTS_DIR / "top_sites.csv"
        rows = []
        
        for run in top_runs:
            site = session.query(Site).filter_by(id=run.site_id).first()
            if not site:
                continue
            
            constraints = session.query(SiteConstraint).filter_by(site_id=site.id).all()
            
            # Get zone and overlays
            zone = ""
            overlays = []
            for c in constraints:
                if c.constraint_type == "zone":
                    zone = c.code
                elif c.constraint_type == "overlay":
                    overlays.append(c.code)
            
            row = {
                "rank": len(rows) + 1,
                "address": site.address_raw,
                "suburb": site.suburb,
                "price_display": site.price_display,
                "price_guide": run.land_cost,
                "land_area_m2": site.land_area_m2 or site.land_size_listed,
                "zone": zone,
                "overlays": "; ".join(overlays),
                "dwellings_base": run.dwellings_base,
                "profit_base": run.profit_base,
                "margin": f"{run.margin_base:.1%}" if run.margin_base else "",
                "score": f"{run.score:.3f}" if run.score else "",
                "url": site.url,
                "manual_review": site.requires_manual_review
            }
            rows.append(row)
            
            # Export individual report
            _export_site_report(site, run, constraints)
        
        # Write CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        console.print(f"[green]Exported {len(rows)} sites to {csv_path}[/green]")
        
        # Print summary table
        _print_summary_table(rows[:10])
        
        return len(rows)


def _export_site_report(site: Site, feas: FeasibilityRun, constraints: list[SiteConstraint]):
    """Export individual site report as Markdown and JSON."""
    
    # Get zone and overlays
    zone = ""
    overlays = []
    for c in constraints:
        if c.constraint_type == "zone":
            zone = c.code
        elif c.constraint_type == "overlay":
            overlays.append({"code": c.code, "severity": c.severity, "desc": c.description})
    
    # Markdown report
    md_path = REPORTS_DIR / f"site_{site.id[:8]}.md"
    
    md_content = f"""# Site Analysis: {site.address_raw}

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Property Details

| Field | Value |
|-------|-------|
| Address | {site.address_raw} |
| Suburb | {site.suburb} |
| Listing Price | {site.price_display or 'Not disclosed'} |
| Land Area | {site.land_area_m2 or site.land_size_listed or 'Unknown'} m² |
| Property Type | {site.property_type} |
| Bedrooms | {site.bedrooms or '-'} |
| Listing URL | [{site.url}]({site.url}) |

## Planning Controls

**Zone**: {zone}

### Overlays
"""
    
    if overlays:
        for o in overlays:
            severity_icon = "🔴" if o["severity"] >= 3 else "🟡" if o["severity"] >= 2 else "🟢"
            md_content += f"\n- {severity_icon} **{o['code']}**: {o['desc']}"
    else:
        md_content += "\n*No overlays apply*"
    
    md_content += f"""

## Feasibility Analysis

### Yield Estimate
- **Low**: {feas.dwellings_low} dwellings
- **Base**: {feas.dwellings_base} dwellings
- **High**: {feas.dwellings_high} dwellings

### Cost Breakdown
| Item | Amount |
|------|--------|
| Land Cost | ${feas.land_cost:,.0f} |
| Build Cost | ${feas.build_cost:,.0f} |
| Soft Costs | ${feas.soft_costs:,.0f} |
| Contingency | ${feas.contingency:,.0f} |
| Holding Costs | ${feas.holding_costs:,.0f} |
| Selling Costs | ${feas.selling_costs:,.0f} |
| **Total Cost** | **${feas.total_cost_base:,.0f}** |

### Revenue & Profit
| Scenario | Revenue | Profit | Margin |
|----------|---------|--------|--------|
| Low | ${feas.revenue_low:,.0f} | ${feas.profit_low:,.0f} | {feas.profit_low/feas.revenue_low:.1%} |
| Base | ${feas.revenue_base:,.0f} | ${feas.profit_base:,.0f} | {feas.margin_base:.1%} |
| High | ${feas.revenue_high:,.0f} | ${feas.profit_high:,.0f} | {feas.profit_high/feas.revenue_high:.1%} |

### Score
**{feas.score:.3f}** (higher = better opportunity)

---

## Notes

"""
    
    if site.requires_manual_review:
        md_content += f"⚠️ **Manual review required**: {site.review_reason}\n"
    else:
        md_content += "✅ No blocking issues identified.\n"
    
    # Assumptions
    if feas.assumptions:
        md_content += f"\n*Assumptions: Build cost ${feas.assumptions.get('build_cost_per_m2', 2800)}/m², "
        md_content += f"Sale price ${feas.assumptions.get('sale_price_per_dwelling', 750000):,}/dwelling*\n"
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    # JSON report
    json_path = REPORTS_DIR / f"site_{site.id[:8]}.json"
    
    json_data = {
        "site_id": site.id,
        "address": site.address_raw,
        "suburb": site.suburb,
        "state": site.state,
        "coordinates": {"lat": site.lat, "lon": site.lon},
        "listing": {
            "price_display": site.price_display,
            "price_guide": site.price_guide,
            "property_type": site.property_type,
            "bedrooms": site.bedrooms,
            "bathrooms": site.bathrooms,
            "land_size_listed": site.land_size_listed,
            "url": site.url
        },
        "parcel": {
            "parcel_id": site.parcel_id,
            "land_area_m2": site.land_area_m2
        },
        "planning": {
            "zone": zone,
            "overlays": overlays
        },
        "feasibility": {
            "dwellings": {
                "low": feas.dwellings_low,
                "base": feas.dwellings_base,
                "high": feas.dwellings_high
            },
            "costs": {
                "land": feas.land_cost,
                "build": feas.build_cost,
                "soft": feas.soft_costs,
                "contingency": feas.contingency,
                "holding": feas.holding_costs,
                "selling": feas.selling_costs,
                "total_base": feas.total_cost_base
            },
            "revenue": {
                "low": feas.revenue_low,
                "base": feas.revenue_base,
                "high": feas.revenue_high
            },
            "profit": {
                "low": feas.profit_low,
                "base": feas.profit_base,
                "high": feas.profit_high
            },
            "margin_base": feas.margin_base,
            "score": feas.score,
            "assumptions": feas.assumptions
        },
        "requires_manual_review": site.requires_manual_review,
        "review_reason": site.review_reason,
        "generated_at": datetime.now().isoformat()
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)


def _print_summary_table(rows: list[dict]):
    """Print a summary table to console."""
    table = Table(title="Top Sites Summary")
    
    table.add_column("#", style="dim")
    table.add_column("Address", style="cyan")
    table.add_column("Suburb")
    table.add_column("Land m²", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Dwellings", justify="right")
    table.add_column("Profit", justify="right", style="green")
    table.add_column("Score", justify="right", style="bold")
    
    for row in rows:
        table.add_row(
            str(row["rank"]),
            row["address"][:40] + "..." if len(row["address"]) > 40 else row["address"],
            row["suburb"],
            f"{row['land_area_m2']:,.0f}" if row["land_area_m2"] else "-",
            row["price_display"] or "-",
            str(row["dwellings_base"]),
            f"${row['profit_base']:,.0f}" if row["profit_base"] else "-",
            row["score"]
        )
    
    console.print(table)


def run():
    """Entry point for report export."""
    export_top_sites()


if __name__ == "__main__":
    run()
