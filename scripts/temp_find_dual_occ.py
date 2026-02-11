import argparse
import asyncio
import csv
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from rich.console import Console

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from scanner.feasibility.dual_occ import DualOccFeasibility
from scanner.ingest.domain import DomainScraper
from scanner.ingest.rea import REAScraper
from scanner.models import Site

console = Console()

TARGET_SUBURBS_FILE = Path("config/suburbs_eastern.txt")
REPORT_PATH = Path("reports/dual_occ_candidates.csv")


async def get_sold_data(suburbs: list[str], scraper) -> dict[str, float]:
    """Get median sold price for 3-4 bed houses to use as GRV proxy."""
    grv_map = {}
    console.print("[bold cyan]Updating GRV/Sold Data...[/bold cyan]")

    # REA Scraper checks
    if hasattr(scraper, "config") and "rea" in str(type(scraper)).lower():
        console.print(
            "[yellow]REA Scraper active - Skipping Live Sold Data (using defaults)[/yellow]"
        )
        return {}

    for sub in suburbs:
        console.print(f"  Getting sold data for {sub}...")
        try:
            listings = await scraper.scrape_suburb(sub, max_pages=1, search_type="sold")

            prices = []
            for l in listings:
                p = scraper.parse_price(l.get("price_text", ""))[2]  # Get mid/value
                if p and p > 800000:  # Filter out anomalies/units
                    prices.append(p)

            if prices:
                prices.sort()
                idx = int(len(prices) * 0.8)
                grv = prices[min(idx, len(prices) - 1)]
                grv_map[sub.lower()] = grv
                console.print(
                    f"  [green]Est GRV for {sub}: ${grv/1e6:.2f}M (n={len(prices)})[/green]"
                )
            else:
                console.print(
                    f"  [yellow]No sold data for {sub}, using default fallback[/yellow]"
                )
                grv_map[sub.lower()] = 1_500_000  # Fallback
        except Exception as e:
            console.print(f"[red]Error fetching sold data: {e}[/red]")
            grv_map[sub.lower()] = 1_500_000

        await asyncio.sleep(2)

    return grv_map


async def find_sites(source: str = "domain"):
    if not TARGET_SUBURBS_FILE.exists():
        console.print("[red]No suburb file found[/red]")
        return

    suburbs = [
        l.strip() for l in TARGET_SUBURBS_FILE.read_text().splitlines() if l.strip()
    ]

    console.print(f"[bold]Starting scan with source: {source.upper()}[/bold]")
    if source == "rea":
        scraper = REAScraper()
    else:
        scraper = DomainScraper()

    await scraper.start()

    try:
        # 1. Get GRV Data
        # We only do a subset to save time for this run, or all if small list
        gr_suburbs = suburbs[:5]  # Limit for demo speed, user can expand
        grv_map = await get_sold_data(gr_suburbs, scraper)

        # 2. Find Sites
        console.print(
            f"\n[bold cyan]Scanning for Sites ({source.upper()})...[/bold cyan]"
        )
        candidates = []

        for sub in suburbs:
            # Scrape Listings
            if source == "rea":
                # REAScraper default scrape_suburb signature
                listings = await scraper.scrape_suburb(sub, max_pages=3)
            else:
                listings = await scraper.scrape_suburb(
                    sub,
                    max_pages=3,
                    search_type="sale",
                    land_size_min=650,  # Dual Occ minimum for Domain
                )

            for l in listings:
                # Convert to Site object for feasibility
                p_low, p_high, p_guide = scraper.parse_price(l.get("price_text", ""))

                # Validate Address
                raw_addr = l.get("address", "")
                url = l.get("url", "")

                # If address looks invalid (contains price or no digits), try to fix from URL
                if (
                    not raw_addr
                    or "$" in raw_addr
                    or not any(c.isdigit() for c in raw_addr)
                ):
                    try:
                        # Extract slug from URL: domain.com.au/address-suburb-listingID
                        # Remove common prefixes/suffixes
                        parts = url.split("domain.com.au/")[-1].split("?")[0]
                        if "/" in parts:
                            parts = parts.split("/")[-1]

                        slug_parts = parts.split("-")
                        # Remove listing ID if it looks like one (last part is long digit)
                        if (
                            slug_parts
                            and slug_parts[-1].isdigit()
                            and len(slug_parts[-1]) > 5
                        ):
                            slug_parts.pop()

                        raw_addr = " ".join(slug_parts).title()
                    except Exception:
                        pass  # Keep original if fix fails

                site = Site(
                    address_raw=raw_addr,
                    suburb=l.get("suburb"),
                    land_size_listed=l.get("land_size_m2"),
                    price_guide=p_guide,
                    price_low=p_low,
                    price_high=p_high,
                )

                # Basic filter (Land Size Check)
                # Domain filters server-side, REA might not so we double check strictly
                if not site.land_size_listed or site.land_size_listed < 650:
                    continue

                # Feasibility
                feas = DualOccFeasibility(site)

                # Look up GRV
                grv = grv_map.get(sub.lower(), 1_500_000)

                result = feas.calculate_margin(grv)

                if result["viable"]:
                    console.print(
                        f"[bold green]FOUND: {site.address_raw} | Margin: {result['margin_percent']:.1f}%[/bold green]"
                    )
                    candidates.append(
                        {
                            "address": site.address_raw,
                            "suburb": site.suburb,
                            "price": site.price_guide,
                            "land": site.land_size_listed,
                            "est_grv": grv,
                            "margin": result["margin_percent"],
                            "profit": result["profit"],
                            "url": l.get("url"),
                            "source": source,
                        }
                    )

            await asyncio.sleep(5)

        # Report
        if candidates:
            new_df = pd.DataFrame(candidates)

            if REPORT_PATH.exists():
                try:
                    existing_df = pd.read_csv(REPORT_PATH)
                    # Combine and deduplicate
                    combined_df = pd.concat([existing_df, new_df])
                    # Keep last to effectively update listing details if re-scraped
                    combined_df = combined_df.drop_duplicates(
                        subset=["address"], keep="last"
                    )

                    combined_df.to_csv(REPORT_PATH, index=False)
                    console.print(
                        f"\n[green]Merged {len(candidates)} new candidates. Total unique: {len(combined_df)}[/green]"
                    )
                except Exception as e:
                    console.print(
                        f"[red]Error merging report: {e}. creating new file.[/red]"
                    )
                    new_df.to_csv(REPORT_PATH, index=False)
            else:
                new_df.to_csv(REPORT_PATH, index=False)
                console.print(
                    f"\n[green]Saved {len(candidates)} candidates to {REPORT_PATH}[/green]"
                )
        else:
            console.print("\n[yellow]No candidates found[/yellow]")

    finally:
        await scraper.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["domain", "rea"], default="domain")
    args = parser.parse_args()

    asyncio.run(find_sites(source=args.source))
