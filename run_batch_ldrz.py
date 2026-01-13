import os
import sys

from rich.console import Console

# Force import from src to pick up local changes
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from scanner.scan_single import scan_single

console = Console()

CANDIDATES = [
    # Donvale
    ("2 Quamby Place, Donvale VIC 3111", 1_725_000),  # Mid-point of 1.65-1.8
    ("26 Heads Road, Donvale VIC 3111", 1_825_000),  # Mid-point of 1.8-1.85
    ("16 Warner Court, Donvale VIC 3111", 1_950_000),  # Lower end guide
    # Warrandyte
    ("16 Margaret Court, Warrandyte VIC 3113", 1_775_000),  # Mid-point 1.7-1.85
    ("13 Clematis Court, Warrandyte VIC 3113", 1_900_000),  # Mid-point 1.85-1.95
    ("5 Jennifer Court, Warrandyte VIC 3113", 1_650_000),  # Listed price
]

console.print("[bold green]STARTING BATCH LDRZ SCAN[/bold green]")

for address, price in CANDIDATES:
    console.print(f"\n[bold]{'#'*60}[/bold]")
    console.print(f"[bold]SCANNING: {address} @ ${price:,.0f}[/bold]")
    console.print(f"[bold]{'#'*60}[/bold]")

    try:
        scan_single(address, purchase_price=price)
    except Exception as e:
        console.print(f"[red]Error scanning {address}: {e}[/red]")
        import traceback

        traceback.print_exc()

console.print("\n[bold green]BATCH SCAN COMPLETE[/bold green]")
console.print("\n[bold green]BATCH SCAN COMPLETE[/bold green]")
