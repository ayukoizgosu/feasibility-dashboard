import os
import sys
import traceback

from rich.console import Console

# Ensure we use local src
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from scanner.scan_single import scan_single

console = Console()

CANDIDATES = [
    # Priority 1: Largest blocks (>10,000 sqm)
    "23 Websters Road, Templestowe",  # 14,200 sqm - TOP CANDIDATE
    # Priority 2: Large blocks (5,000-10,000 sqm)
    "319 Oban Road, Donvale",  # 5,211 sqm
    "15 Vincent Road, Park Orchards",  # 5,389 sqm at $2.7-2.95M
    "14 Amersham Drive, Warrandyte",  # 6,374 sqm
    # Previously identified with potential
    "63 South Valley Road, Park Orchards",  # 10,740 sqm - showed subdivision potential
]


def run_batch():
    console.print(
        f"[bold blue]Running LDRZ Batch Scan for {len(CANDIDATES)} New Candidates...[/bold blue]"
    )

    results = []

    for address in CANDIDATES:
        console.print(f"\n[bold magenta]Scanning: {address}[/bold magenta]")
        try:
            # Run scan (assuming default strategy for now, LDRZ logic is embedded)
            scan_single(address)
            results.append((address, "Completed"))
        except Exception as e:
            console.print(f"[red]Error scanning {address}: {e}[/red]")
            traceback.print_exc()


if __name__ == "__main__":
    run_batch()
