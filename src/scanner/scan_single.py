import requests
from rich.console import Console

from scanner.constraints.quick_kill import evaluate_quick_kill

console = Console()


def geocode_address(address: str):
    """Geocode address using Nominatim."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "au"}
    headers = {"User-Agent": "SiteScanner/1.0"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return None

        return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]
    except Exception as e:
        console.print(f"[red]Geocoding failed: {e}[/red]")
        return None


def extract_suburb(address: str) -> str | None:
    """Extract suburb name from address string.

    OSM Nominatim format: "Street, Suburb, City, LGA, State, Postcode, Country"
    Example: "63, South Valley Road, Park Orchards, Melbourne, City of Manningham, Victoria, 3114, Australia"
    """
    # Known LDRZ suburbs we're searching for
    KNOWN_SUBURBS = {
        "donvale",
        "templestowe",
        "park orchards",
        "warrandyte",
        "warrandyte south",
        "wonga park",
        "eltham",
        "eltham north",
        "research",
        "chirnside park",
        "montrose",
        "mount evelyn",
        "kangaroo ground",
        "north warrandyte",
        "lower plenty",
        "templestowe lower",
        "viewbank",
        "bulleen",
    }

    # Try to find suburb from comma-separated address
    parts = [p.strip().lower() for p in address.split(",")]

    # First, check for known suburbs explicitly
    for part in parts:
        if part in KNOWN_SUBURBS:
            return part.title()

    # Fallback: look for suburb pattern (typically 3rd part from street)
    if len(parts) >= 3:
        # Check parts 2-4 (after street address, before city/state)
        for i in range(1, min(4, len(parts))):
            part = parts[i].strip()
            # Remove state/postcode indicators and street names
            if (
                part
                and not part.isdigit()
                and part.upper()
                not in ("VIC", "NSW", "QLD", "VICTORIA", "AUSTRALIA", "MELBOURNE")
                and not part.startswith("city of")
                # Skip street names (e.g., "dryden street")
                and not any(
                    part.endswith(suffix)
                    for suffix in [
                        " street",
                        " road",
                        " avenue",
                        " drive",
                        " lane",
                        " court",
                        " place",
                        " crescent",
                    ]
                )
            ):
                return part.title()

    return None


def scan_single(
    address: str,
    purchase_price: float | None = None,
    quality: str = "Standard",
    dual_occ: bool = False,
):
    """Scan a single property for development potential.

    Args:
        address: Property address
        purchase_price: Optional purchase price for feasibility
        quality: Target build quality (Basic, Standard, Premium, Luxury)
        dual_occ: If True, analyze as dual-occupancy (2x townhouses)
    """
    console.print(f"\n[bold blue]{'='*60}[/bold blue]")
    console.print(f"[bold blue]SCANNING: {address}[/bold blue]")
    console.print(f"[bold blue]{'='*60}[/bold blue]")

    # 1. Geocode
    result = geocode_address(address)
    if not result:
        console.print("[red]Could not find address coordinates.[/red]")
        return

    lat, lon, found_address = result
    suburb = extract_suburb(found_address)
    console.print(f"[green]Found:[/green] {found_address}")
    console.print(f"[dim]Lat: {lat}, Lon: {lon}[/dim]")
    if suburb:
        console.print(f"[dim]Suburb: {suburb}[/dim]")

    # 2. Run Quick Kill
    console.print("\n[bold]1. QUICK-KILL CONSTRAINT CHECK[/bold]")
    kill_result = evaluate_quick_kill(lat, lon)

    if kill_result.should_reject:
        status_color = "red"
        status_text = "REJECTED"
    else:
        status_color = "green"
        status_text = "PASS"

    console.print(f"Status: [{status_color}]{status_text}[/{status_color}]")

    if kill_result.reasons:
        console.print("[bold red]Rejection Reasons:[/bold red]")
        for reason in kill_result.reasons:
            console.print(f" - {reason}")

    if kill_result.warnings:
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for warning in kill_result.warnings:
            console.print(f" - {warning}")

    if kill_result.should_reject:
        console.print("[dim]Skipping Deep Dive due to rejection.[/dim]")
        return

    # 3. Deep Dive Assessment
    console.print("\n[bold]2. DEEP DIVE ASSESSMENT[/bold]")

    from scanner.feasibility.model import calculate_simple_feasibility
    from scanner.spatial.geometry import (
        calculate_approx_area_sqm,
        calculate_frontage,
        calculate_orientation,
        calculate_slope_and_elevation,
        get_property_polygon,
    )

    console.print("Fetching Parcel...")
    poly = get_property_polygon(lat, lon)

    if not poly:
        console.print("[yellow]Could not fetch parcel geometry.[/yellow]")
        return

    area = calculate_approx_area_sqm(poly)
    console.print(f"[green]Parcel Area: ~{area:.0f} sqm[/green]")

    # Geometry analysis
    slope, elev, slope_note = calculate_slope_and_elevation(poly)
    frontage, f_notes = calculate_frontage(poly)
    bearing, orient = calculate_orientation(poly)

    console.print(f"Slope: {slope:.1f}% ({slope_note})")
    if slope > 12.0:
        console.print("[red]⚠️ High Risk: Slope > 12%[/red]")

    console.print(f"Frontage: {frontage:.1f}m")
    console.print(f"Orientation: {orient} ({bearing:.0f}°)")

    # Check Zoning
    console.print("\n[bold]Checking Planning Zone...[/bold]")
    try:
        from scanner.spatial.zone_cache import get_zone_at_point_cached

        zone_info = get_zone_at_point_cached(lat, lon)
        if zone_info:
            code = zone_info.get("code")
            lga = zone_info.get("lga")
            source = "Cache" if zone_info.get("cached") else "WFS (Live)"
            console.print(f"[green]Zone: {code} ({lga})[/green] [dim][{source}][/dim]")
        else:
            console.print("[yellow]Could not determine zone.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error checking zone: {e}[/red]")

    # check school zones
    console.print("\n[bold]Checking School Zones...[/bold]")
    try:
        from scanner.db import get_session
        from scanner.spatial.school_checks import check_school_zones

        with get_session() as session:
            school_matches = check_school_zones(lat, lon, session)
            if school_matches:
                for sm in school_matches:
                    rank_info = (
                        f" (Rank: {sm['rank_score']})" if sm["rank_score"] else ""
                    )
                    console.print(
                        f"[green]🎓 In Zone: {sm['school_name']} ({sm['school_type']}){rank_info}[/green]"
                    )
                    if sm.get("rank_description"):
                        console.print(f"   [dim]{sm['rank_description']}[/dim]")
            else:
                console.print("[dim]No high-ranking school zones found in cache.[/dim]")
    except Exception as e:
        console.print(f"[red]Error checking school zones: {e}[/red]")

    # 4. LDRZ Assessment (if land is large enough)
    if area >= 3000:  # Only check LDRZ for larger blocks
        console.print("\n[bold]3. LDRZ SUBDIVISION ASSESSMENT[/bold]")

        try:
            from scanner.spatial.ldrz_checks import (
                assess_ldrz_subdivision,
                print_ldrz_assessment,
            )
            from scanner.spatial.transmission_cache import (
                check_transmission_proximity_cached,
                ensure_transmission_cache,
            )

            # Check transmission lines
            transmission_info = None
            try:
                ensure_transmission_cache()
                is_near, dist, line_info = check_transmission_proximity_cached(
                    lat, lon, 500
                )
                if is_near and line_info:
                    transmission_info = {
                        "voltage_kv": line_info.get("voltage_kv", 0),
                        "distance_m": dist,
                    }
                    console.print(
                        f"[yellow]⚡ Transmission line: {line_info.get('voltage_kv')}kV at {dist:.0f}m[/yellow]"
                    )
            except Exception as e:
                console.print(f"[dim]Transmission check skipped: {e}[/dim]")

            # Run LDRZ assessment
            ldrz = assess_ldrz_subdivision(
                lat,
                lon,
                area,
                suburb=suburb,
                transmission_info=transmission_info,
            )
            print_ldrz_assessment(ldrz)

            # If LDRZ feasible, calculate profitability
            if ldrz.is_ldrz and ldrz.subdividable:
                console.print("\n[bold]4. LDRZ FEASIBILITY CALCULATION[/bold]")

                from scanner.feasibility.ldrz_strategy import (
                    calculate_ldrz_feasibility,
                    print_ldrz_feasibility,
                )

                # Use provided price or estimate from land rate
                if purchase_price is None:
                    # Estimate purchase price from area
                    land_rate = 500  # Conservative $/sqm for LDRZ
                    purchase_price = area * land_rate
                    console.print(
                        f"[dim]Estimated purchase price: ${purchase_price:,.0f} (at ${land_rate}/sqm)[/dim]"
                    )

                feas = calculate_ldrz_feasibility(
                    purchase_price=purchase_price,
                    land_size_sqm=area,
                    has_sewerage=ldrz.sewerage.likely_sewered or False,
                    suburb=suburb,
                    holding_months=12,
                )
                print_ldrz_feasibility(feas)

        except ImportError as e:
            console.print(f"[yellow]LDRZ module not available: {e}[/yellow]")
        except Exception as e:
            console.print(f"[red]LDRZ assessment error: {e}[/red]")

    # 5. Standard Feasibility (for smaller blocks or comparison)
    if area < 3000 or True:  # Always run standard feasibility
        console.print("\n[bold]5. STANDARD DEVELOPMENT FEASIBILITY[/bold]")

        from scanner.planning.rules import calculate_max_footprint, check_yield_limits

        zone_code = "GRZ1"  # Default/Placeholder
        max_foot, notes = calculate_max_footprint(area, zone_code)
        yield_cap = check_yield_limits(zone_code)

        if yield_cap:
            notes.append(f"Yield Capped: {yield_cap}")

        console.print("[bold]Planning Constraints (GRZ1 Assumed):[/bold]")
        for note in notes:
            console.print(f" - {note}")

        if purchase_price is None:
            analysis_type = "Dual-Occ" if dual_occ else "Single Dwelling"
            console.print(
                f"\n[bold cyan]📊 Market Intelligence (GRV Analysis - {analysis_type}, {quality}):[/bold cyan]"
            )
            try:
                if dual_occ:
                    # Use dedicated dual-occ analysis
                    from scanner.market.intel import get_dual_occ_grv_analysis

                    grv = get_dual_occ_grv_analysis(
                        suburb=suburb or "Unknown",
                        land_area_sqm=area,
                        townhouse_sqm_each=150,
                        target_quality=quality,
                        months_lookback=12,
                    )

                    # Display dual-occ specific output
                    ev = grv["end_value_per_unit"]
                    console.print("\n[bold]End Value Estimate (Per Townhouse):[/bold]")
                    if ev.get("estimate"):
                        console.print(
                            f"  [green]Per Unit: ${ev['estimate']:,.0f}[/green] × 2 = "
                            f"[bold green]${ev['estimate'] * 2:,.0f}[/bold green]"
                        )
                        console.print(
                            f"  [dim]Confidence: {ev.get('confidence', 'N/A').upper()} | "
                            f"Source: {ev.get('data_source', 'N/A')}[/dim]"
                        )
                    else:
                        console.print("  [yellow]No townhouse data available[/yellow]")

                    # Land value
                    lv = grv["land_value"]
                    if lv.get("land_rate_psm"):
                        console.print("\n[bold]Land Value Estimate:[/bold]")
                        console.print(
                            f"  Land Rate: [cyan]${lv['land_rate_psm']:,.0f}/sqm[/cyan]"
                        )
                        console.print(
                            f"  Implied Land Value: [cyan]${lv['estimated_land_value']:,.0f}[/cyan]"
                        )
                        land_price = lv["estimated_land_value"]
                    else:
                        land_price = 1_500_000

                    # Construction
                    cc = grv["construction"]
                    console.print(
                        "\n[bold]Construction Cost (2x 150sqm Townhouses):[/bold]"
                    )
                    console.print(
                        f"  Per Unit Build: ${cc['per_unit']['construction']:,.0f}"
                    )
                    console.print(
                        f"  × 2 Units: ${cc['per_unit']['construction'] * 2:,.0f}"
                    )
                    console.print(
                        f"  + Demo: ${cc['demolition']:,.0f} | Landscaping: ${cc['landscaping']:,.0f} | Site: ${cc['site_costs']:,.0f}"
                    )
                    console.print(
                        f"  [bold]Total Build Cost: ${cc['total']:,.0f}[/bold]"
                    )

                    # Feasibility
                    feas_data = grv.get("feasibility")
                    if feas_data:
                        console.print("\n[bold]Dual-Occ Feasibility Summary:[/bold]")
                        console.print(
                            f"  Total End Value (2 units): ${feas_data['total_end_value']:,.0f}"
                        )
                        console.print(
                            f"  Land Cost:                -${feas_data['land_cost']:,.0f}"
                        )
                        console.print(
                            f"  Construction:             -${feas_data['construction_cost']:,.0f}"
                        )
                        console.print("  ─────────────────────")

                        margin_color = "green" if feas_data["viable"] else "red"
                        console.print(
                            f"  [bold]Gross Profit:              [{margin_color}]${feas_data['gross_profit']:,.0f}[/{margin_color}][/bold]"
                        )
                        console.print(
                            f"  [bold]Margin:                    [{margin_color}]{feas_data['margin_pct']:.1f}%[/{margin_color}][/bold]"
                        )
                        console.print(
                            f"  [dim]Profit per unit: ${feas_data['profit_per_unit']:,.0f}[/dim]"
                        )

                        if feas_data["viable"]:
                            console.print(
                                "  [green]✅ VIABLE (≥18% margin for dual-occ)[/green]"
                            )
                        else:
                            console.print("  [red]❌ NOT VIABLE (<18% margin)[/red]")

                else:
                    # Standard single-dwelling analysis
                    from scanner.market.intel import get_grv_analysis

                    grv = get_grv_analysis(
                        suburb=suburb or "Unknown",
                        land_area_sqm=area,
                        proposed_building_sqm=200,
                        property_type="House",
                        target_quality=quality,
                        months_lookback=12,
                    )

                    # End Value Section
                    ev = grv["end_value"]
                    if ev["estimate"]:
                        console.print("\n[bold]End Value Estimate:[/bold]")
                        console.print(
                            f"  [green]Adjusted Median: ${ev['estimate']:,.0f}[/green] "
                            f"[dim](Raw: ${ev['estimate_raw']:,.0f})[/dim]"
                        )
                        console.print(
                            f"  [dim]Confidence: {ev['confidence'].upper()} | "
                            f"Method: {ev['search_method']} | "
                            f"Comps: {ev['comps_count']}[/dim]"
                        )

                        # Price range
                        pr = ev["price_range"]
                        console.print(
                            f"  [dim]Range: ${pr['min']:,.0f} - ${pr['max']:,.0f}[/dim]"
                        )

                        # Show top 3 adjusted comps
                        if ev["comps"]:
                            console.print("\n  [bold]Top Comparables:[/bold]")
                            for i, comp in enumerate(ev["comps"][:3], 1):
                                adj_note = (
                                    f" ({comp['adjustment_pct']})"
                                    if comp["adjustment_pct"] != "+0.0%"
                                    else ""
                                )
                                console.print(
                                    f"    {i}. {comp['address'][:40]}... "
                                    f"- ${comp['adjusted_price']:,.0f}{adj_note}"
                                )
                                console.print(
                                    f"       [dim]Sold ${comp['sold_price']:,.0f} on {comp['sold_date']}, "
                                    f"{comp['land_area']:.0f}sqm[/dim]"
                                )

                    # Land Value Section
                    lv = grv["land_value"]
                    if lv["land_rate_psm"]:
                        console.print("\n[bold]Land Value Estimate:[/bold]")
                        console.print(
                            f"  Land Rate: [cyan]${lv['land_rate_psm']:,.0f}/sqm[/cyan]"
                        )
                        console.print(
                            f"  Implied Land Value: [cyan]${lv['estimated_land_value']:,.0f}[/cyan]"
                        )
                        console.print(f"  [dim]Method: {lv['method']}[/dim]")
                        land_price = lv["estimated_land_value"]
                    else:
                        land_price = ev["estimate"] if ev["estimate"] else 1_500_000

                    # Construction Cost Section
                    cc = grv["construction"]
                    console.print("\n[bold]Construction Cost Estimate (200sqm):[/bold]")
                    console.print(
                        f"  Build: ${cc['construction']:,.0f} @ ${cc['rate_psm']:,.0f}/sqm ({cc['quality_tier']})"
                    )
                    console.print(
                        f"  + Demo: ${cc['demolition']:,.0f} | Landscaping: ${cc['landscaping']:,.0f} | Fees: ${cc['professional_fees']:,.0f}"
                    )
                    console.print(
                        f"  [bold]Total Build Cost: ${cc['total']:,.0f}[/bold]"
                    )

                    # Feasibility Summary
                    feas_data = grv["feasibility"]
                    if feas_data:
                        console.print("\n[bold]GRV Feasibility Summary:[/bold]")
                        console.print(
                            f"  End Value:        ${feas_data['end_value']:,.0f}"
                        )
                        console.print(
                            f"  Land Cost:       -${feas_data['land_cost']:,.0f}"
                        )
                        console.print(
                            f"  Construction:    -${feas_data['construction_cost']:,.0f}"
                        )
                        console.print("  ─────────────────────")

                        margin_color = "green" if feas_data["viable"] else "red"
                        console.print(
                            f"  [bold]Gross Profit:      [{margin_color}]${feas_data['gross_profit']:,.0f}[/{margin_color}][/bold]"
                        )
                        console.print(
                            f"  [bold]Margin:            [{margin_color}]{feas_data['margin_pct']:.1f}%[/{margin_color}][/bold]"
                        )

                        if feas_data["viable"]:
                            console.print("  [green]✅ VIABLE (≥15% margin)[/green]")
                        else:
                            console.print("  [red]❌ NOT VIABLE (<15% margin)[/red]")

            except Exception as e:
                console.print(f"[yellow]GRV analysis unavailable: {e}[/yellow]")
                import traceback

                traceback.print_exc()
                land_price = 1_500_000
        else:
            land_price = purchase_price

        feas = calculate_simple_feasibility(
            land_price=land_price,
            land_area_sqm=area,
            strategy="DualOcc" if frontage > 18 else "Single",
            max_footprint_sqm=max_foot,
            max_dwellings=yield_cap,
        )

        console.print(f"\n[bold]Feasibility (${land_price/1e6:.2f}M Purchase):[/bold]")
        console.print(f"Strategy: {feas.strategy}")
        console.print(f"GDV: ${feas.gdv/1000000:.2f}M")
        console.print(f"TDC: ${feas.tdc/1000000:.2f}M")
        console.print(f"Margin: {feas.margin_percent:.1f}%")
        if feas.notes:
            console.print(f"Notes: {'; '.join(feas.notes)}")

        if feas.is_viable:
            console.print("[green]Outcome: VIABLE ✓[/green]")
        else:
            console.print("[yellow]Outcome: Low Margin ⚠️[/yellow]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scan a single property.")
    parser.add_argument("address", nargs="?", help="Property address to scan")
    parser.add_argument(
        "--price", type=float, default=None, help="Purchase price override"
    )
    parser.add_argument(
        "--quality",
        type=str,
        choices=["Basic", "Standard", "Premium", "Luxury"],
        default="Standard",
        help="Target build quality tier",
    )
    parser.add_argument(
        "--dual-occ",
        action="store_true",
        help="Analyze as dual-occupancy (2x townhouses)",
    )

    args = parser.parse_args()

    if args.address:
        scan_single(
            args.address,
            purchase_price=args.price,
            quality=args.quality,
            dual_occ=args.dual_occ,
        )
    else:
        # Fallback to test addresses if no argument provided
        print("No address provided. Running default test:")
        scan_single("2 Quamby Place, Donvale VIC 3111", purchase_price=1_750_000)
