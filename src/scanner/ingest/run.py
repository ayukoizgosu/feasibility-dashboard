"""Run all ingest methods - scrapers first, API as fallback."""

import asyncio
import random
from rich.console import Console

from scanner.db import init_db

console = Console()


async def run_all():
    """Run ingestion - scrapers primary, API fallback."""
    console.print("[bold]Starting listing ingestion...[/bold]\n")
    
    init_db()
    
    total = 0
    scraper_failed = False
    
    # 1. Domain scraper (primary - human-like)
    console.print("[bold cyan]1. Domain Scraper[/bold cyan]")
    try:
        from scanner.ingest.domain import scrape_domain
        count = await scrape_domain()
        total += count
        if count == 0:
            scraper_failed = True
    except Exception as e:
        console.print(f"[yellow]Domain scraper error: {e}[/yellow]")
        scraper_failed = True
    
    # Random delay between sources
    await asyncio.sleep(random.uniform(10, 30))
    
    # 2. REA scraper (human-like)
    console.print("\n[bold cyan]2. REA Scraper[/bold cyan]")
    try:
        from scanner.ingest.rea import scrape_rea
        count = await scrape_rea()
        total += count
    except Exception as e:
        console.print(f"[yellow]REA scraper error: {e}[/yellow]")
    
    # 3. Manual CSV import
    console.print("\n[bold cyan]3. Manual CSV Import[/bold cyan]")
    try:
        from scanner.ingest.manual import run as run_manual
        run_manual()
    except Exception as e:
        console.print(f"[dim]No CSV files found[/dim]")
    
    # 4. Domain API (LAST RESORT - only if scrapers failed)
    if scraper_failed and total == 0:
        console.print("\n[bold yellow]4. Domain API (fallback)[/bold yellow]")
        try:
            from scanner.ingest.domain_api import ingest_domain_api
            count = await ingest_domain_api()
            total += count
        except Exception as e:
            console.print(f"[dim]API fallback unavailable: {e}[/dim]")
    
    console.print(f"\n[bold green]Ingestion complete. {total} new listings.[/bold green]")


def run():
    """Entry point."""
    asyncio.run(run_all())


if __name__ == "__main__":
    run()
