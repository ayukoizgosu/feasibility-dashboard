"""Weekly refresh for LDRZ 2-lot candidates."""

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

from scanner.config import get_config
from scanner.db import init_db, get_session
from scanner.geocode.nominatim import geocode_pending_sites
from scanner.ingest.domain import scrape_domain
from scanner.ingest.rea import scrape_rea
from scanner.models import Site
from scanner.spatial.ldrz_checks import estimate_sewerage_availability, is_ldrz_zone
from scanner.spatial.zone_cache import get_zone_at_point_cached

console = Console()

DEFAULT_SUBURBS_FILE = Path("config/suburbs_metro_east.txt")
DEFAULT_STATE_FILE = Path("db/weekly_refresh_state.json")


def load_suburbs(path: Path) -> list[str]:
    if not path.exists():
        return []

    suburbs = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        suburbs.append(line)

    return suburbs


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"index": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"index": 0}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def select_batch(suburbs: list[str], batch_size: int, state: dict) -> list[str]:
    if not suburbs:
        return []

    start = state.get("index", 0) % len(suburbs)
    end = start + batch_size

    if end <= len(suburbs):
        batch = suburbs[start:end]
    else:
        batch = suburbs[start:] + suburbs[: end - len(suburbs)]

    state["index"] = end % len(suburbs)
    return batch


async def ingest_and_geocode(
    domain_suburbs: list[str],
    rea_suburbs: list[str],
    geocode_limit: int,
) -> None:

    if domain_suburbs:
        console.print(f"[bold]Domain suburbs:[/bold] {', '.join(domain_suburbs)}")
    if rea_suburbs:
        console.print(f"[bold]REA suburbs:[/bold] {', '.join(rea_suburbs)}")

    domain_count = 0
    if domain_suburbs:
        domain_count = await scrape_domain(suburbs=domain_suburbs)
    
    rea_count = 0
    if rea_suburbs:
        rea_count = await scrape_rea(suburbs=rea_suburbs)
        
    console.print(f"[green]Ingested: Domain {domain_count}, REA {rea_count}[/green]")

    if geocode_limit > 0:
        success, failed = await geocode_pending_sites(limit=geocode_limit)
        console.print(f"[green]Geocoded: {success} success, {failed} failed[/green]")


def _price_estimate(site: Site) -> float | None:
    if site.price_guide:
        return site.price_guide
    if site.price_low and site.price_high:
        return (site.price_low + site.price_high) / 2
    return None


def _sewer_status(note: str, likely_sewered: bool | None) -> str:
    if likely_sewered is True:
        return "likely_sewered"
    if likely_sewered is False:
        return "likely_unsewered"
    if "partial" in (note or "").lower():
        return "partial"
    return "unknown"


def collect_candidates(
    min_area: int,
    max_area: int,
    require_ldrz: bool,
    zone_cache_days: int,
    price_max: int | None,
    property_types: list[str],
) -> list[dict]:
    rows = []

    with get_session() as session:
        sites = session.query(Site).all()

        for site in sites:
            size = site.land_area_m2 or site.land_size_listed
            if not size:
                continue
            if size < min_area or size > max_area:
                continue

            if site.property_type and site.property_type not in property_types:
                continue

            price_est = _price_estimate(site)
            if price_max and price_est and price_est > price_max:
                continue

            if site.lat is None or site.lon is None:
                continue

            zone_code = None
            zone_cached = False
            if require_ldrz:
                zone_info = get_zone_at_point_cached(
                    site.lat,
                    site.lon,
                    max_age_days=zone_cache_days,
                )
                if zone_info:
                    zone_code = zone_info.get("code")
                    zone_cached = bool(zone_info.get("cached"))

                if not zone_code or not is_ldrz_zone(zone_code):
                    continue

            sewer = estimate_sewerage_availability(site.lat, site.lon, site.suburb)
            sewer_status = _sewer_status(sewer.note, sewer.likely_sewered)

            if sewer.likely_sewered is True:
                two_lot_possible = "yes" if size >= min_area else "no"
            elif sewer.likely_sewered is False:
                two_lot_possible = "yes" if size >= max_area else "no"
            else:
                two_lot_possible = "verify"

            land_source = "parcel" if site.land_area_m2 else "listing"

            rows.append(
                {
                    "address": site.address_raw or "",
                    "suburb": site.suburb or "",
                    "land_size_m2": int(size),
                    "land_source": land_source,
                    "price_display": site.price_display or "",
                    "price_est": int(price_est) if price_est else "",
                    "url": site.url or "",
                    "source": site.source or "",
                    "last_seen": site.last_seen.isoformat() if site.last_seen else "",
                    "zone_code": zone_code or "",
                    "zone_cached": "yes" if zone_cached else "no",
                    "sewer_status": sewer_status,
                    "two_lot_possible": two_lot_possible,
                    "sewer_note": sewer.note,
                }
            )

    rows.sort(key=lambda r: r.get("last_seen", ""), reverse=True)
    return rows


def write_report(rows: list[dict], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "address",
        "suburb",
        "land_size_m2",
        "land_source",
        "price_display",
        "price_est",
        "url",
        "source",
        "last_seen",
        "zone_code",
        "zone_cached",
        "sewer_status",
        "two_lot_possible",
        "sewer_note",
    ]

    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    console.print(f"[green]Report written:[/green] {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Weekly refresh for LDRZ 2-lot candidates."
    )
    parser.add_argument(
        "--suburbs-file",
        type=Path,
        default=DEFAULT_SUBURBS_FILE,
        help="Path to suburb list file (one suburb per line)",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="Path to rotation state JSON",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--rea-batch-size", type=int, default=2)
    parser.add_argument("--geocode-limit", type=int, default=500)
    parser.add_argument("--min-area", type=int, default=4000)
    parser.add_argument("--max-area", type=int, default=8000)
    parser.add_argument("--zone-cache-days", type=int, default=30)
    parser.add_argument(
        "--skip-ldrz-check",
        action="store_true",
        help="Skip LDRZ zoning confirmation (size-only)",
    )
    parser.add_argument("--report-dir", type=Path, default=Path("reports"))
    parser.add_argument(
        "--source",
        choices=["domain", "rea", "both", "random"],
        default="random",
        help="Source to scrape (default: random)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_db()

    config = get_config()
    suburbs = load_suburbs(args.suburbs_file) or config.suburbs

    if not suburbs:
        console.print("[red]No suburbs available for refresh[/red]")
        return

    if args.batch_size > 4:
        console.print("[yellow]Batch size limited to 4 for Domain[/yellow]")
        args.batch_size = 4
    if args.rea_batch_size > 2:
        console.print("[yellow]REA batch size limited to 2[/yellow]")
        args.rea_batch_size = 2

    state = load_state(args.state_file)
    batch = select_batch(suburbs, args.batch_size, state)
    save_state(args.state_file, state)

    rea_batch = batch[: args.rea_batch_size]

    # Select source
    target_source = args.source
    if target_source == "random":
        import random
        target_source = random.choice(["domain", "rea"])
    
    console.print("[bold blue]Starting weekly refresh[/bold blue]")
    console.print(f"[dim]Batch index: {state.get('index', 0)}[/dim]")
    console.print(f"[bold yellow]Stealth Mode: Scanning {target_source.upper()} only[/bold yellow]")

    domain_targets = []
    rea_targets = []

    if target_source == "domain":
        domain_targets = batch
    elif target_source == "rea":
        rea_targets = rea_batch
    else:  # both
        domain_targets = batch
        rea_targets = rea_batch

    asyncio.run(ingest_and_geocode(domain_targets, rea_targets, args.geocode_limit))

    rows = collect_candidates(
        min_area=args.min_area,
        max_area=args.max_area,
        require_ldrz=not args.skip_ldrz_check,
        zone_cache_days=args.zone_cache_days,
        price_max=config.filters.price_max,
        property_types=config.filters.property_types,
    )

    report_name = f"weekly_ldrz_candidates_{datetime.now():%Y%m%d}.csv"
    report_path = args.report_dir / report_name
    write_report(rows, report_path)

    latest_path = args.report_dir / "weekly_ldrz_candidates_latest.csv"
    write_report(rows, latest_path)

    console.print(f"[green]Candidates found: {len(rows)}[/green]")


if __name__ == "__main__":
    main()
