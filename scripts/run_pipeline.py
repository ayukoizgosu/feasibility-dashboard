"""End-to-end pipeline runner."""

import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

# Add src to path
sys.path.insert(0, str(__file__).replace("scripts/run_pipeline.py", "src"))

from scanner.db import init_db
from scanner.ingest.domain import scrape_domain
from scanner.ingest.rea import scrape_rea
from scanner.geocode.nominatim import geocode_pending_sites
from scanner.spatial.resolve import resolve_parcels
from scanner.constraints.evaluate import evaluate_site_constraints
from scanner.feasibility.model import run_feasibility
from scanner.reporting.export import export_top_sites

console = Console()


async def run_pipeline():
    """Run the complete site scanner pipeline."""
    
    console.print(Panel.fit(
        "[bold blue]Melbourne Property Site Scanner[/bold blue]\n"
        f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="🏠 Site Scanner"
    ))
    
    # Step 1: Initialize database
    console.print("\n[bold]Step 1: Initialize Database[/bold]")
    init_db()
    
    # Step 2: Scrape listings
    console.print("\n[bold]Step 2: Scrape Listings[/bold]")
    domain_count = await scrape_domain()
    rea_count = await scrape_rea()
    console.print(f"  Total new listings: {domain_count + rea_count}")
    
    # Step 3: Geocode
    console.print("\n[bold]Step 3: Geocode Addresses[/bold]")
    success, failed = await geocode_pending_sites()
    console.print(f"  Geocoded: {success} success, {failed} failed")
    
    # Step 4: Resolve parcels
    console.print("\n[bold]Step 4: Resolve Parcels[/bold]")
    matched, unmatched = resolve_parcels()
    console.print(f"  Parcels: {matched} matched, {unmatched} unmatched")
    
    # Step 5: Evaluate constraints
    console.print("\n[bold]Step 5: Evaluate Constraints[/bold]")
    evaluated = evaluate_site_constraints()
    console.print(f"  Evaluated: {evaluated} sites")
    
    # Step 6: Run feasibility
    console.print("\n[bold]Step 6: Calculate Feasibility[/bold]")
    analyzed = run_feasibility()
    console.print(f"  Analyzed: {analyzed} sites")
    
    # Step 7: Export reports
    console.print("\n[bold]Step 7: Export Reports[/bold]")
    exported = export_top_sites()
    console.print(f"  Exported: {exported} sites")
    
    console.print(Panel.fit(
        f"[bold green]Pipeline Complete![/bold green]\n"
        f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📊 Reports available in: reports/",
        title="✅ Done"
    ))


def main():
    """Entry point."""
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
