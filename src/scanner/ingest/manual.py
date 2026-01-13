"""Manual/CSV listing import for REA and other sources.

Since REA (realestate.com.au) explicitly prohibits scraping and uses
sophisticated bot detection (Kasada), the realistic options are:

1. Manual entry via CSV import
2. Licensed data feed (partner agreement with REA)
3. Use Domain API only (covers many same listings)

This module provides CSV import functionality.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from scanner.config import get_config
from scanner.models import RawListing, Site
from scanner.db import get_session

console = Console()

# Expected CSV columns
EXPECTED_COLUMNS = [
    "address",
    "suburb", 
    "postcode",
    "price",
    "land_size_m2",
    "property_type",
    "bedrooms",
    "bathrooms",
    "url",
    "source"  # 'rea', 'manual', etc.
]

# Sample CSV template
CSV_TEMPLATE = """address,suburb,postcode,price,land_size_m2,property_type,bedrooms,bathrooms,url,source
"123 Smith Street","Preston","3072","1200000","650","house","3","2","https://...","manual"
"45 Example Road","Reservoir","3073","950000","720","house","4","2","https://...","manual"
"""


def generate_csv_template(output_path: Path | str = None) -> Path:
    """Generate a template CSV file for manual listing entry."""
    if output_path is None:
        output_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "listings_template.csv"
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write(CSV_TEMPLATE)
    
    console.print(f"[green]Template created: {output_path}[/green]")
    return output_path


def import_listings_csv(csv_path: Path | str) -> int:
    """Import listings from a CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Number of listings imported
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        console.print(f"[red]File not found: {csv_path}[/red]")
        return 0
    
    config = get_config()
    imported = 0
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        with get_session() as session:
            for i, row in enumerate(reader):
                try:
                    address = row.get("address", "").strip()
                    if not address:
                        continue
                    
                    suburb = row.get("suburb", "").strip()
                    source = row.get("source", "manual").strip().lower()
                    
                    # Generate a unique ID
                    listing_id = f"{source}_{i}_{hash(address) % 100000}"
                    raw_id = f"{source}:{listing_id}"
                    
                    # Skip if exists
                    if session.query(RawListing).filter_by(id=raw_id).first():
                        continue
                    
                    # Parse price
                    price_str = row.get("price", "").replace(",", "").replace("$", "")
                    price = float(price_str) if price_str.isdigit() else None
                    
                    # Parse land size
                    land_str = row.get("land_size_m2", "").replace(",", "")
                    land_size = float(land_str) if land_str else None
                    
                    # Parse bedrooms/bathrooms
                    beds = int(row.get("bedrooms", 0) or 0)
                    baths = int(row.get("bathrooms", 0) or 0)
                    
                    # Create raw listing
                    raw = RawListing(
                        id=raw_id,
                        source=source,
                        listing_id=listing_id,
                        url=row.get("url"),
                        payload=dict(row)
                    )
                    session.add(raw)
                    
                    # Create site
                    site = Site(
                        source=source,
                        rea_listing_id=listing_id if source == "rea" else None,
                        url=row.get("url"),
                        address_raw=address,
                        suburb=suburb,
                        postcode=row.get("postcode"),
                        state="VIC",
                        property_type=row.get("property_type", "house"),
                        price_guide=price,
                        price_display=row.get("price"),
                        bedrooms=beds if beds else None,
                        bathrooms=baths if baths else None,
                        land_size_listed=land_size,
                        geocode_status="pending"
                    )
                    session.add(site)
                    imported += 1
                    
                except Exception as e:
                    console.print(f"[yellow]Row {i} error: {e}[/yellow]")
    
    console.print(f"[green]Imported {imported} listings from CSV[/green]")
    return imported


def run():
    """Check for and import any CSV files in data directory."""
    from scanner.db import init_db
    init_db()
    
    data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"
    
    # Look for any listings*.csv files
    csv_files = list(data_dir.glob("listings*.csv"))
    
    if not csv_files:
        console.print("[yellow]No listings CSV files found in data/[/yellow]")
        console.print("[dim]Create one using: python -c \"from scanner.ingest.manual import generate_csv_template; generate_csv_template()\"[/dim]")
        return
    
    total = 0
    for csv_file in csv_files:
        console.print(f"[blue]Importing: {csv_file.name}[/blue]")
        total += import_listings_csv(csv_file)
    
    console.print(f"[green]Total imported: {total}[/green]")


if __name__ == "__main__":
    run()
