"""Evaluate planning constraints for sites."""

import uuid

from rich.console import Console
from shapely import Point, wkt

from scanner.config import get_config
from scanner.db import get_session
from scanner.feasibility.model import calculate_simple_feasibility
from scanner.models import PlanningOverlay, PlanningZone, Site, SiteConstraint
from scanner.spatial.geometry import (
    calculate_approx_area_sqm,
    calculate_frontage,
    calculate_orientation,
    calculate_slope_and_elevation,
    get_property_polygon,
)

console = Console()


def evaluate_site_constraints(site_id: str = None) -> int:
    """Evaluate planning constraints for sites.

    Args:
        site_id: Optional specific site to evaluate (all if None)

    Returns:
        Number of sites evaluated
    """
    config = get_config()
    evaluated = 0

    with get_session() as session:
        # Get sites to evaluate
        query = session.query(Site).filter(Site.lat.isnot(None), Site.lon.isnot(None))

        if site_id:
            query = query.filter(Site.id == site_id)

        sites = query.all()

        if not sites:
            console.print("[yellow]No geocoded sites to evaluate[/yellow]")
            return 0

        console.print(f"[blue]Evaluating constraints for {len(sites)} sites...[/blue]")

        # Load all zones and overlays for spatial matching
        zones = session.query(PlanningZone).all()
        overlays = session.query(PlanningOverlay).all()

        console.print(f"  Loaded {len(zones)} zones, {len(overlays)} overlays")

        # Build simple spatial index for zones/overlays
        zone_grid: dict[tuple[int, int], list[PlanningZone]] = {}
        for zone in zones:
            if zone.centroid_lat and zone.centroid_lon:
                key = (int(zone.centroid_lat * 10), int(zone.centroid_lon * 10))
                if key not in zone_grid:
                    zone_grid[key] = []
                zone_grid[key].append(zone)

        overlay_grid: dict[tuple[int, int], list[PlanningOverlay]] = {}
        for overlay in overlays:
            if overlay.centroid_lat and overlay.centroid_lon:
                key = (int(overlay.centroid_lat * 10), int(overlay.centroid_lon * 10))
                if key not in overlay_grid:
                    overlay_grid[key] = []
                overlay_grid[key].append(overlay)

        for i, site in enumerate(sites):
            # Clear existing constraints
            session.query(SiteConstraint).filter_by(site_id=site.id).delete()

            site_point = Point(site.lon, site.lat)
            site_key = (int(site.lat * 10), int(site.lon * 10))

            # ==================================================================
            # STEP 1: Quick-Kill Screening
            # ==================================================================
            from scanner.constraints.quick_kill import evaluate_quick_kill

            # Run quick-kill check (cache-first)
            qk_result = evaluate_quick_kill(site.lat, site.lon)

            if qk_result.should_reject:
                # Add constraints for rejection reasons
                for reason in qk_result.reasons:
                    details = {}
                    if "details" in qk_result.details:
                        # Extract specific details if available
                        msg_lower = reason.lower()
                        if "transmission" in msg_lower:
                            details = qk_result.details.get("transmission_line", {})
                        elif "heritage" in msg_lower:
                            details = qk_result.details.get("heritage", {})

                    constraint = SiteConstraint(
                        site_id=site.id,
                        constraint_key=f"quick_kill:{uuid.uuid4().hex[:8]}",
                        constraint_type="quick_kill",
                        code="BLOCKER",
                        severity=5,  # Maximum severity
                        description=reason,
                        details=details,
                    )
                    session.add(constraint)

                # Mark as rejected/high severity
                site.requires_manual_review = False  # Auto-rejected, don't waste time
                site.review_reason = (
                    f"REJECTED by Quick-Kill: {'; '.join(qk_result.reasons)}"
                )

                evaluated += 1
                if (i + 1) % 100 == 0:
                    console.print(f"  Progress: {i + 1}/{len(sites)}")
                    session.commit()
                continue  # SKIP detailed analysis

            # ==================================================================
            # STEP 1.5: Geometry & Feasibility (Deep Dive)
            # ==================================================================
            # Only run if passed Quick Kill.
            # Note: This involves WFS calls, so slightly slower.

            try:
                # 1. Fetch Parcel
                parcel_poly = get_property_polygon(site.lat, site.lon)

                if parcel_poly:
                    # 2. Slope & Elevation
                    slope, elev, slope_note = calculate_slope_and_elevation(parcel_poly)

                    # 3. Frontage & Orientation
                    frontage, frontage_notes = calculate_frontage(parcel_poly)
                    bearing, orientation_desc = calculate_orientation(parcel_poly)

                    # Check Slope Risk (>12% = High Risk/Reject)
                    if slope > 12.0:
                        constraint = SiteConstraint(
                            site_id=site.id,
                            constraint_key=f"geom_slope:{uuid.uuid4().hex[:8]}",
                            constraint_type="geometry",
                            code="SLOPE_HIGH",
                            severity=5,  # Reject
                            description=f"Steep Slope: {slope:.1f}% (>12%)",
                            details={
                                "slope": slope,
                                "elevation": elev,
                                "note": slope_note,
                            },
                        )
                        session.add(constraint)
                        # Mark as rejected
                        site.requires_manual_review = False
                        site.review_reason = f"REJECTED: Slope > 12% ({slope:.1f}%)"
                        session.commit()
                        evaluated += 1
                        continue  # Skip further analysis

                    # Add Geometry info as informational constraint
                    geo_constraint = SiteConstraint(
                        site_id=site.id,
                        constraint_key=f"geom_info:{uuid.uuid4().hex[:8]}",
                        constraint_type="geometry",
                        code="INFO",
                        severity=1,
                        description=f"Frontage: {frontage:.1f}m, Slope: {slope:.1f}%, Rear: {orientation_desc}",
                        details={
                            "frontage": frontage,
                            "slope": slope,
                            "elevation": elev,
                            "orientation": bearing,
                            "orientation_desc": orientation_desc,
                        },
                    )
                    session.add(geo_constraint)

                    # 4. Feasibility
                    # Get actual price from site data if available
                    parsed_price = site.price_guide
                    if not parsed_price and site.price_low and site.price_high:
                        parsed_price = (site.price_low + site.price_high) / 2
                    if not parsed_price:
                        parsed_price = 1_000_000.0  # Default fallback

                    approx_area = calculate_approx_area_sqm(parcel_poly)

                    # 4. Planning & Feasibility
                    from scanner.planning.rules import (
                        calculate_max_footprint,
                        check_yield_limits,
                    )

                    # Determine zone (use first zone found or default)
                    zone_code = "GRZ1"
                    # Quick check for zone constraint in this loop already?
                    # We haven't run zone check yet (it's below).
                    # Ideally we should run zone check BEFORE deep dive or integrate it.
                    # For now, let's try to detect zone from database if it exists, otherwise default.
                    # Or run zone check for this site simply now.
                    # Simplified: Assume GRZ1 for now, or fetch if available.

                    # Calculate constraints
                    max_total_footprint, planning_notes = calculate_max_footprint(
                        approx_area, zone_code
                    )
                    yield_cap = check_yield_limits(zone_code)

                    if yield_cap:
                        planning_notes.append(f"Yield Cap: {yield_cap} dwellings")

                    feas_result = calculate_simple_feasibility(
                        land_price=parsed_price,
                        land_area_sqm=approx_area,
                        strategy="DualOcc" if frontage > 18.0 else "Single",
                        max_footprint_sqm=max_total_footprint,
                        max_dwellings=yield_cap,
                    )

                    if feas_result.is_viable:
                        severity = 0  # Good
                        desc = f"Feasible: {feas_result.strategy} (Margin {feas_result.margin_percent:.1f}%)"
                    else:
                        severity = 3  # Warning
                        desc = f"Low Margin: {feas_result.margin_percent:.1f}% ({feas_result.strategy})"

                    # Append planning notes to description/details
                    if planning_notes:
                        desc += f" [{'; '.join(planning_notes)}]"

                    feas_constraint = SiteConstraint(
                        site_id=site.id,
                        constraint_key=f"feasibility:{uuid.uuid4().hex[:8]}",
                        constraint_type="feasibility",
                        code="MARGIN_CHECK",
                        severity=severity,
                        description=desc,
                        details={
                            "gdv": feas_result.gdv,
                            "tdc": feas_result.tdc,
                            "margin": feas_result.margin_percent,
                            "notes": feas_result.notes,
                            "planning_constraints": planning_notes,
                        },
                    )
                    session.add(feas_constraint)

            except Exception as e:
                console.print(f"[red]Error in Deep Dive for site {site.id}: {e}[/red]")

            # ==================================================================
            # STEP 2: Detailed Spatial Analysis
            # ==================================================================

            # Find zone
            zone_found = False
            for dlat in range(-2, 3):
                for dlon in range(-2, 3):
                    key = (site_key[0] + dlat, site_key[1] + dlon)
                    if key not in zone_grid:
                        continue

                    for zone in zone_grid[key]:
                        try:
                            zone_geom = wkt.loads(zone.geom_wkt)
                            if zone_geom.contains(site_point):
                                constraint = SiteConstraint(
                                    site_id=site.id,
                                    constraint_key=f"zone:{zone.zone_code}",
                                    constraint_type="zone",
                                    code=zone.zone_code,
                                    severity=0,  # Zones are informational
                                    description=f"Zoned {zone.zone_code}",
                                    details={"lga": zone.lga, "zone": zone.zone_code},
                                )
                                session.add(constraint)
                                zone_found = True
                                break
                        except Exception:
                            continue

                    if zone_found:
                        break
                if zone_found:
                    break

            # Find overlays
            max_severity = 0
            for dlat in range(-2, 3):
                for dlon in range(-2, 3):
                    key = (site_key[0] + dlat, site_key[1] + dlon)
                    if key not in overlay_grid:
                        continue

                    for overlay in overlay_grid[key]:
                        try:
                            overlay_geom = wkt.loads(overlay.geom_wkt)
                            if overlay_geom.contains(site_point):
                                severity = config.get_constraint_severity(
                                    overlay.overlay_code
                                )
                                max_severity = max(max_severity, severity)

                                # Get description based on overlay type
                                descriptions = {
                                    "HO": "Heritage Overlay - development restrictions apply",
                                    "DDO": "Design & Development Overlay - height/setback limits",
                                    "SLO": "Significant Landscape Overlay - vegetation controls",
                                    "ESO": "Environmental Significance Overlay - referral required",
                                    "BMO": "Bushfire Management Overlay - BAL assessment needed",
                                    "LSIO": "Land Subject to Inundation - floor level requirements",
                                    "SBO": "Special Building Overlay - flood study may be needed",
                                    "PAO": "Public Acquisition Overlay - development unlikely",
                                    "EAO": "Environmental Audit Overlay - contamination check",
                                    "NCO": "Neighbourhood Character - design guidelines",
                                }

                                desc = descriptions.get(
                                    overlay.overlay_type,
                                    f"{overlay.overlay_type} overlay applies",
                                )

                                constraint = SiteConstraint(
                                    site_id=site.id,
                                    constraint_key=f"overlay:{overlay.overlay_code}",
                                    constraint_type="overlay",
                                    code=overlay.overlay_code,
                                    severity=severity,
                                    description=desc,
                                    details={
                                        "lga": overlay.lga,
                                        "type": overlay.overlay_type,
                                    },
                                )
                                session.add(constraint)
                        except Exception:
                            continue

            # Mark for manual review if high severity
            if max_severity >= 3:
                site.requires_manual_review = True
                site.review_reason = "High severity constraint (Heritage/PAO/EAO)"

            evaluated += 1

            if (i + 1) % 100 == 0:
                console.print(f"  Progress: {i + 1}/{len(sites)}")
                session.commit()

    console.print(f"[green]Evaluated constraints for {evaluated} sites[/green]")
    return evaluated


def run():
    """Entry point for constraint evaluation."""
    evaluate_site_constraints()


if __name__ == "__main__":
    run()
