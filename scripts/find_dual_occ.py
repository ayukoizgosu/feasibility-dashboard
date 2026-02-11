import argparse
import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
from rich.console import Console

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from scanner.feasibility.dual_occ import DualOccFeasibility
from scanner.ingest.domain import DomainScraper
from scanner.ingest.rea import REAScraper
from scanner.market.database import get_db, get_suburb_stats, init_db, save_comparable
from scanner.models import Site

# Initialize DB
init_db()

console = Console()

TARGET_SUBURBS_FILE = Path("config/suburbs_eastern.txt")
REPORT_PATH = Path("reports/dual_occ_candidates.csv")


async def get_sold_data(suburbs: list[str], scraper) -> dict[str, dict]:
    """Get median sold price for 3-4 bed houses to use as GRV proxy."""
    grv_map = {}
    console.print("[bold cyan]Updating GRV/Sold Data...[/bold cyan]")

    for sub in suburbs:
        # Check DB first
        try:
            with next(get_db()) as db:
                stats = get_suburb_stats(db, sub)
                if stats and stats["count"] >= 10:
                    console.print(
                        f"  [dim]Using DB stats for {sub} (n={stats['count']})[/dim]"
                    )
                    grv_map[sub.lower()] = {
                        "value": stats["p80"],
                        "median": stats["median"],
                        "count": stats["count"],
                        "min": stats["min"],
                        "max": stats["max"],
                    }
                    continue
        except Exception as db_e:
            console.print(f"[dim]DB lookup failed for {sub}: {db_e}[/dim]")

        # REA Scraper checks (it has sold scraper now)
        is_rea = "rea" in str(type(scraper)).lower()

        console.print(f"  Fetching fresh sold data for {sub}...")
        try:
            if is_rea:
                listings = await scraper.scrape_sold(sub, max_pages=1)
            else:
                listings = await scraper.scrape_suburb(
                    sub,
                    max_pages=1,
                    search_type="sold",
                    property_types=["house", "townhouse"],
                )

            prices = []
            for listing in listings:
                # Save to DB first
                try:
                    with next(get_db()) as db:
                        save_comparable(db, listing)
                except Exception as db_e:
                    console.print(f"[red]DB Save Error: {db_e}[/red]")

                # Get price for map
                p = listing.get("sold_price")
                if not p:
                    # Fallback parse
                    from scanner.market.utils import parse_sold_price

                    p = parse_sold_price(listing.get("price_text", ""))

                if p and p > 600000:
                    prices.append(p)

            if prices:
                prices.sort()
                grv = prices[int(len(prices) * 0.8) if len(prices) > 1 else 0]
                median_price = prices[len(prices) // 2]

                grv_map[sub.lower()] = {
                    "value": grv,
                    "median": median_price,
                    "count": len(prices),
                    "min": prices[0],
                    "max": prices[-1],
                }
                console.print(
                    f"  [green]Est GRV for {sub}: ${grv/1e6:.2f}M (n={len(prices)}) | Median: ${median_price/1e6:.2f}M[/green]"
                )
            else:
                console.print(
                    f"  [yellow]No sold data for {sub}, using default[/yellow]"
                )
                grv_map[sub.lower()] = {
                    "value": 1_500_000,
                    "median": 1_300_000,
                    "count": 0,
                }

        except Exception as e:
            console.print(f"[red]Error fetching sold data: {e}[/red]")
            grv_map[sub.lower()] = {"value": 1_500_000, "median": 1_300_000, "count": 0}

    return grv_map


async def find_sites(source: str = "domain"):
    if not TARGET_SUBURBS_FILE.exists():
        console.print("[red]No suburb file found[/red]")
        return

    suburbs = [
        sub_line.strip()
        for sub_line in TARGET_SUBURBS_FILE.read_text().splitlines()
        if sub_line.strip()
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

            for listing in listings:
                # Convert to Site object for feasibility
                p_low, p_high, p_guide = scraper.parse_price(
                    listing.get("price_text", "")
                )

                raw_addr = listing.get("address", "")
                url = listing.get("url", "")

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
                    suburb=listing.get("suburb"),
                    land_size_listed=listing.get("land_size_m2"),
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
                grv_data = grv_map.get(
                    sub.lower(), {"value": 1_500_000, "median": 1_300_000, "count": 0}
                )
                grv_val = grv_data["value"]

                result = feas.calculate_margin(grv_val)

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
                            "est_grv": grv_val,
                            "grv_median": grv_data["median"],
                            "grv_sold_count": grv_data["count"],
                            "margin": result["margin_percent"],
                            "profit": result["profit"],
                            "url": listing.get("url"),
                            "source": source,
                            # Detailed Feasibility
                            "product_type": result["product"],
                            "target_gfa": result["target_gfa_sq"],
                            "build_rate": result["build_rate_m2"],
                            "est_build_cost": result["est_construction_cost"],
                            "acq_cost": result["site_acquisition_cost"],
                            "finance_cost": result["finance_cost"],
                            "consultants": result["consultants_fees"],
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
    parser.add_argument(
        "--output", default="reports/dual_occ_candidates.csv", help="Output report path"
    )
    args = parser.parse_args()

    # Update global path based on arg
    REPORT_PATH = Path(args.output)

    asyncio.run(find_sites(source=args.source))
