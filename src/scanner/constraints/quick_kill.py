"""Quick-kill screening for property sites.

Implements fast rejection rules:
1. Within 300m of high-voltage transmission lines (66kV+)
2. Heritage Overlay (HO) or Victorian Heritage Register (VHR) listing
3. Bushfire Management Overlay (BMO) or Bushfire Prone Area (BPA)
4. Public Acquisition Overlay (PAO) or Environmental Audit Overlay (EAO)
5. Proximity to Substations, Power Stations, EPA Priority Sites
"""

from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.models import Site, SiteConstraint

# New Modules
from scanner.spatial.data_vic_checks import (
    check_bushfire_prone_area,
    check_enviro_audit_sites,
    check_epa_priority_sites,
)
from scanner.spatial.ga_infrastructure import (
    check_power_station_proximity,
    check_substation_proximity,
)
from scanner.spatial.gis_clients import (
    check_blocker_overlays,
    check_heritage_register,
    check_property_easements,
    check_transmission_proximity,
)

console = Console()


@dataclass
class QuickKillResult:
    """Result of quick-kill screening."""

    should_reject: bool = False
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def add_warning(
        self, warning: str, detail_key: str = None, detail_value: Any = None
    ):
        """Add a warning (does not reject)."""
        self.warnings.append(warning)
        if detail_key:
            self.details[detail_key] = detail_value

    def add_reason(self, reason: str, detail_key: str = None, detail_value: Any = None):
        """Add a rejection reason."""
        self.should_reject = True
        self.reasons.append(reason)
        if detail_key:
            self.details[detail_key] = detail_value


def evaluate_quick_kill(
    lat: float,
    lon: float,
    transmission_threshold_m: float = 300,
    blocker_overlay_types: list[str] | None = None,
) -> QuickKillResult:
    """Fast pre-screen using GIS APIs.

    Checks for hard blockers that should reject a site immediately,
    before running detailed constraint analysis.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        transmission_threshold_m: Max distance to HV transmission lines (default 300m)
        blocker_overlay_types: Overlay types that cause rejection

    Returns:
        QuickKillResult with rejection status, reasons, and details
    """
    if blocker_overlay_types is None:
        # Default blocker overlays: Heritage, BMO, PAO, EAO, BMO
        blocker_overlay_types = ["HO", "VHR", "PAO", "EAO", "BMO"]

    result = QuickKillResult()

    # ==========================================================================
    # CHECK 1: Transmission line proximity (use cache first, fallback to WFS)
    # ==========================================================================
    try:
        # Try cached check first (fast local query)
        from scanner.spatial.transmission_cache import (
            check_transmission_proximity_cached,
        )

        is_near, distance_m, line_info = check_transmission_proximity_cached(
            lat, lon, transmission_threshold_m
        )

        # If no cached data, fallback to WFS (slower)
        if distance_m is None:
            console.print("[dim]No cached transmission data, trying WFS...[/dim]")
            is_near, distance_m, line_info = check_transmission_proximity(
                lat, lon, transmission_threshold_m
            )

        if is_near and distance_m is not None:
            voltage = line_info.get("voltage_kv", "unknown") if line_info else "unknown"
            result.add_reason(
                f"Within {distance_m:.0f}m of {voltage}kV transmission line",
                "transmission_line",
                {
                    "distance_m": distance_m,
                    "voltage_kv": voltage,
                    "owner": line_info.get("owner") if line_info else None,
                },
            )
    except Exception as e:
        console.print(f"[yellow]Transmission line check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 2: Blocker planning overlays (HO, BMO, PAO, EAO)
    # ==========================================================================
    try:
        from scanner.spatial.overlay_cache import check_overlays_cached, has_cache_data

        blockers = []
        if has_cache_data():
            # Use local cache
            found = check_overlays_cached(lat, lon)
            # Filter for blocker types
            blockers = [o for o in found if o.get("type") in blocker_overlay_types]
        else:
            # Fallback to WFS
            blockers = check_blocker_overlays(lat, lon, blocker_overlay_types)

        for overlay in blockers:
            overlay_code = overlay.get("code", "Unknown")
            overlay_type = overlay.get("type", "")

            # Build human-readable description
            descriptions = {
                "HO": "Heritage Overlay - development restrictions apply",
                "VHR": "Victorian Heritage Register listing",
                "BMO": "Bushfire Management Overlay - BAL assessment + design constraints",
                "PAO": "Public Acquisition Overlay - land may be acquired",
                "EAO": "Environmental Audit Overlay - contamination assessment required",
            }
            desc = descriptions.get(overlay_type, f"{overlay_type} overlay applies")

            result.add_reason(
                f"{overlay_code}: {desc}", f"overlay_{overlay_type.lower()}", overlay
            )
    except Exception as e:
        console.print(f"[yellow]Overlay check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 3: Victorian Heritage Register (separate from HO overlay)
    # ==========================================================================
    try:
        heritage_items = check_heritage_register(lat, lon)

        for item in heritage_items:
            vhr_number = item.get("vhr_number") or "Unknown"
            name = item.get("name") or "Heritage item"

            result.add_reason(f"VHR {vhr_number}: {name}", "heritage_register", item)
    except Exception as e:
        console.print(f"[yellow]Heritage register check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 4: Easements (Vicmap Property Approved Easements)
    # ==========================================================================
    try:
        has_blockers, has_any, easements = check_property_easements(lat, lon)

        if has_blockers:
            # REJECT: Major infrastructure easements (drainage, sewer, HV, gas)
            blocker_easements = [e for e in easements if e.get("severity", 0) >= 3]
            types_found = [e.get("easement_type", "unknown") for e in blocker_easements]
            result.add_reason(
                f"Major infrastructure easement: {', '.join(set(types_found))}",
                "easement_blocker",
                blocker_easements,
            )
        elif has_any:
            # WARNING: Other easements present (access, fencing, etc.)
            for e in easements:
                severity = e.get("severity", 0)
                desc = e.get("description", "Unknown easement")
                if severity == 2:
                    result.add_warning(
                        f"Access/utility easement: {desc}",
                        "easement_warning",
                        e,
                    )
                elif severity == 1:
                    result.add_warning(
                        f"Minor easement: {desc}",
                        "easement_info",
                        e,
                    )

    except Exception as e:
        console.print(f"[yellow]Easement check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 5: Feng Shui (Substations, Reservoirs, T-Junctions)
    # ==========================================================================
    try:
        from scanner.spatial.feng_shui_cache import (
            check_puz1_proximity,
            check_road_node_proximity,
            check_water_proximity,
        )

        # 5a. Substations (PUZ1 Proxy) - REJECT
        is_puz1, subst_item = check_puz1_proximity(lat, lon, radius_m=50)
        if is_puz1:
            result.add_reason(
                "Within 50m of Utility/Substation Zone (PUZ1)",
                "substation_proxy",
                subst_item,
            )

        # 5b. Reservoirs (Water) - WARNING
        is_water, water_item = check_water_proximity(lat, lon, radius_m=50)
        if is_water:
            result.add_warning(
                "Near Water Reservoir/Tank (<50m)", "water_proximity", water_item
            )

        # 5c. T-Junctions (Road Nodes) - WARNING
        is_junction, node_item = check_road_node_proximity(lat, lon, radius_m=20)
        if is_junction:
            result.add_warning(
                "Potential T-Junction/Road End (<20m)", "t_junction_proxy", node_item
            )

    except Exception as e:
        console.print(f"[yellow]Feng Shui check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 6: Bushfire Prone Area (BPA)
    # ==========================================================================
    try:
        is_bpa, bpa_info = check_bushfire_prone_area(lat, lon)
        if is_bpa:
            # BPA is just a Warning for now, unless configured otherwise
            # but usually it adds cost, doesn't kill the deal.
            result.add_warning(
                "Located in Bushfire Prone Area (BPA) - construction costs apply",
                "bushfire_prone_area",
                bpa_info,
            )
    except Exception as e:
        console.print(f"[yellow]BPA check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 7: EPA Priority Sites (Contamination)
    # ==========================================================================
    try:
        epa_sites = check_epa_priority_sites(lat, lon, radius_m=500)
        if epa_sites:
            # Find closest
            closest_site = min(
                epa_sites,
                key=lambda x: x.get("properties", {}).get("distance_m", float("inf")),
            )
            dist_m = closest_site["properties"].get("distance_m", 0)

            # Found contamination - REJECT
            result.add_reason(
                f"Within {dist_m:.0f}m of EPA Priority Site (Contamination) [Rec: >500m]",
                "epa_priority_sites",
                closest_site,
            )
    except Exception as e:
        console.print(f"[yellow]EPA PSR check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 8: Infrastructure (Substations, Power Stations - Actual)
    # ==========================================================================
    try:
        # Substations (GA Data) - 200m
        is_subst, dist, info = check_substation_proximity(lat, lon, radius_m=200)
        if is_subst:
            dist_str = f"{dist:.0f}m" if dist else "<200m"
            result.add_reason(
                f"Within {dist_str} of Electrical Substation [Rec: >200m]",
                "substation_infrastructure",
                info,
            )

        # Power Stations - 1000m (Updated threshold)
        is_ps, dist, info = check_power_station_proximity(lat, lon, radius_m=1000)
        if is_ps:
            dist_str = f"{dist:.0f}m" if dist else "<1000m"
            result.add_reason(
                f"Within {dist_str} of Major Power Station [Rec: >1000m]",
                "power_station",
                info,
            )
    except Exception as e:
        console.print(f"[yellow]Infrastructure check failed: {e}[/yellow]")

    # ==========================================================================
    # CHECK 9: Environmental Audits (Proxy for Landfills/Industrial Risk)
    # ==========================================================================
    try:
        audit_sites = check_enviro_audit_sites(lat, lon, radius_m=1000)
        if audit_sites:
            closest = min(
                audit_sites,
                key=lambda x: x.get("properties", {}).get("distance_m", float("inf")),
            )
            dist_m = closest["properties"].get("distance_m", 0)

            result.add_warning(
                f"Within {dist_m:.0f}m of Environmental Audit Site (Potential Contamination/Landfill) [Rec: >1000m]",
                "enviro_audit_site",
                closest,
            )
    except Exception as e:
        console.print(f"[yellow]Enviro Audit check failed: {e}[/yellow]")

    return result


def run_quick_kill_screen(site_ids: list[str] | None = None) -> dict[str, int]:
    """Run quick-kill screening on sites in database.

    Args:
        site_ids: Optional list of specific site IDs to screen (all if None)

    Returns:
        Dict with counts: {'screened': N, 'rejected': N, 'passed': N, 'failed': N}
    """
    config = get_config()

    # Get quick-kill settings from config
    qk_config = config._raw.get("quick_kill", {})
    transmission_threshold = qk_config.get("transmission_line_proximity_m", 300)
    blocker_types = qk_config.get(
        "blocker_overlays", ["HO", "VHR", "PAO", "EAO", "BMO"]
    )

    counts = {"screened": 0, "rejected": 0, "passed": 0, "failed": 0}

    with get_session() as session:
        # Get sites with geocoded coordinates that haven't been rejected yet
        query = session.query(Site).filter(
            Site.lat.isnot(None),
            Site.lon.isnot(None),
            Site.listing_status != "rejected",
        )

        if site_ids:
            query = query.filter(Site.id.in_(site_ids))

        sites = query.all()

        if not sites:
            console.print("[yellow]No sites to screen[/yellow]")
            return counts

        console.print(f"[blue]Quick-kill screening {len(sites)} sites...[/blue]")
        console.print(f"  Transmission threshold: {transmission_threshold}m")
        console.print(f"  Blocker overlays: {', '.join(blocker_types)}")

        for i, site in enumerate(sites):
            counts["screened"] += 1

            try:
                result = evaluate_quick_kill(
                    site.lat,
                    site.lon,
                    transmission_threshold_m=transmission_threshold,
                    blocker_overlay_types=blocker_types,
                )

                if result.should_reject:
                    # Mark site as rejected
                    site.listing_status = "rejected"
                    site.requires_manual_review = False
                    site.review_reason = "; ".join(result.reasons)

                    # Create constraint record
                    constraint = SiteConstraint(
                        site_id=site.id,
                        constraint_key="quick_kill",
                        constraint_type="auto_reject",
                        severity=3,
                        description=site.review_reason,
                        details=result.details,
                    )
                    session.add(constraint)

                    counts["rejected"] += 1
                    console.print(
                        f"  [red]✗[/red] {site.address_raw}: {result.reasons[0]}"
                    )
                else:
                    if result.warnings:
                        console.print(
                            f"  [yellow]![/yellow] {site.address_raw}: {result.warnings[0]}"
                        )
                    counts["passed"] += 1

            except Exception as e:
                console.print(f"  [yellow]![/yellow] {site.address_raw}: Error - {e}")
                counts["failed"] += 1

            # Commit periodically
            if (i + 1) % 50 == 0:
                session.commit()
                console.print(f"  Progress: {i + 1}/{len(sites)}")

        session.commit()

    console.print("\n[bold]Quick-kill results:[/bold]")
    console.print(f"  Screened: {counts['screened']}")
    console.print(f"  [red]Rejected: {counts['rejected']}[/red]")
    console.print(f"  [green]Passed: {counts['passed']}[/green]")
    if counts["failed"]:
        console.print(f"  [yellow]Failed: {counts['failed']}[/yellow]")

    return counts


def run():
    """Entry point for quick-kill screening."""
    run_quick_kill_screen()


if __name__ == "__main__":
    run()
    run()
