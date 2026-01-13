"""LDRZ (Low Density Residential Zone) subdivision checks.

Provides analysis functions for LDRZ subdivision opportunities:
- Zone detection and minimum lot size calculation
- Sewerage availability heuristics
- Overlay restriction assessment
- Subdivision feasibility calculation
"""

from dataclasses import dataclass
from typing import Any

from rich.console import Console

from scanner.spatial.gis_clients import get_overlays_at_point, get_zones_at_point

console = Console()


# =============================================================================
# LDRZ ZONE DETECTION
# =============================================================================

LDRZ_ZONE_CODES = {
    "LDRZ",
    "LDRZ1",
    "LDRZ2",
    "LDRZ-",
    "LOW DENSITY RESIDENTIAL",
}


def is_ldrz_zone(zone_code: str) -> bool:
    """Check if zone code is Low Density Residential Zone.

    Args:
        zone_code: Zone code string from planning data

    Returns:
        True if zone is LDRZ variant
    """
    if not zone_code:
        return False
    upper = zone_code.upper().strip()
    return any(upper.startswith(ldrz) for ldrz in LDRZ_ZONE_CODES)


def get_ldrz_min_lot_size(has_sewerage: bool) -> int:
    """Get minimum lot size for LDRZ subdivision.

    Args:
        has_sewerage: Whether property has reticulated sewerage

    Returns:
        Minimum lot size in square meters
    """
    # Victorian planning scheme standard:
    # With sewerage: 2,000 sqm (0.2 ha)
    # Without sewerage: 4,000 sqm (0.4 ha)
    return 2000 if has_sewerage else 4000


# =============================================================================
# OVERLAY RESTRICTIONS
# =============================================================================

# Overlays that may restrict or complicate subdivision
RESTRICTIVE_OVERLAYS = {
    # High impact - may prevent subdivision
    "ESO": ("Environmental Significance Overlay", "HIGH"),
    "SLO": ("Significant Landscape Overlay", "HIGH"),
    "VPO": ("Vegetation Protection Overlay", "HIGH"),
    "BMO": ("Bushfire Management Overlay", "HIGH"),
    "LSIO": ("Land Subject to Inundation Overlay", "HIGH"),
    "FO": ("Floodway Overlay", "HIGH"),
    # Medium impact - adds complexity
    "NCO": ("Neighbourhood Character Overlay", "MEDIUM"),
    "DDO": ("Design and Development Overlay", "MEDIUM"),
    "DPO": ("Development Plan Overlay", "MEDIUM"),
    "HO": ("Heritage Overlay", "MEDIUM"),
    # Low impact - minor requirements
    "EAO": ("Environmental Audit Overlay", "LOW"),
}


@dataclass
class OverlayAssessment:
    """Result of overlay restriction assessment."""

    has_restrictions: bool
    high_risk_overlays: list[str]
    medium_risk_overlays: list[str]
    low_risk_overlays: list[str]
    notes: list[str]
    can_subdivide: bool  # False if HIGH risk overlay blocks subdivision


def assess_overlays_for_subdivision(
    lat: float,
    lon: float,
) -> OverlayAssessment:
    """Assess planning overlays that may restrict subdivision.

    Args:
        lat: Latitude in WGS84
        lon: Longitude in WGS84

    Returns:
        OverlayAssessment with categorized risks
    """
    overlays = get_overlays_at_point(lat, lon)

    high_risk = []
    medium_risk = []
    low_risk = []
    notes = []

    for overlay in overlays:
        overlay_code = overlay.get("code", "")
        if not overlay_code:
            continue

        # Extract base overlay code (e.g., "ESO1" -> "ESO")
        base_code = "".join(c for c in overlay_code if not c.isdigit()).upper()

        if base_code in RESTRICTIVE_OVERLAYS:
            name, severity = RESTRICTIVE_OVERLAYS[base_code]

            if severity == "HIGH":
                high_risk.append(f"{overlay_code}: {name}")
                notes.append(f"⚠️ {overlay_code} may restrict subdivision")
            elif severity == "MEDIUM":
                medium_risk.append(f"{overlay_code}: {name}")
                notes.append(f"📋 {overlay_code} requires additional approvals")
            else:
                low_risk.append(f"{overlay_code}: {name}")

    has_restrictions = bool(high_risk or medium_risk or low_risk)
    can_subdivide = len(high_risk) == 0  # Can proceed if no HIGH risk overlays

    return OverlayAssessment(
        has_restrictions=has_restrictions,
        high_risk_overlays=high_risk,
        medium_risk_overlays=medium_risk,
        low_risk_overlays=low_risk,
        notes=notes,
        can_subdivide=can_subdivide,
    )


# =============================================================================
# SEWERAGE HEURISTICS
# =============================================================================

# Suburbs in Manningham/Yarra Ranges with known sewerage coverage
# This is a heuristic - always verify with water authority
SEWERED_SUBURBS = {
    # Manningham - mostly sewered
    "donvale": True,
    "templestowe": True,
    "templestowe lower": True,
    "bulleen": True,
    "doncaster": True,
    "doncaster east": True,
    "park orchards": "partial",  # Check each property
    "warrandyte": "partial",  # Many on septic
    "wonga park": "partial",
    # Nillumbik - often unsewered
    "eltham": True,
    "eltham north": "partial",
    "research": False,
    "kangaroo ground": False,
    "hurstbridge": False,
    "diamond creek": True,
    # Yarra Ranges
    "chirnside park": True,
    "mooroolbark": True,
    "lilydale": True,
    "mount evelyn": "partial",
    "montrose": "partial",
    "kilsyth": True,
}


@dataclass
class SewerageAssessment:
    """Result of sewerage availability heuristic check."""

    likely_sewered: bool | None  # None = unknown
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    min_lot_size: int
    note: str
    verification_required: bool


def estimate_sewerage_availability(
    lat: float,
    lon: float,
    suburb: str | None = None,
) -> SewerageAssessment:
    """Estimate sewerage availability based on suburb heuristics.

    IMPORTANT: This is a heuristic only. Always verify with Yarra Valley Water
    (1300 304 688) before purchase.

    Args:
        lat: Latitude
        lon: Longitude
        suburb: Suburb name (optional, will be extracted from geocode if not provided)

    Returns:
        SewerageAssessment with likelihood and confidence
    """
    if suburb:
        suburb_lower = suburb.lower().strip()

        if suburb_lower in SEWERED_SUBURBS:
            status = SEWERED_SUBURBS[suburb_lower]

            if status is True:
                return SewerageAssessment(
                    likely_sewered=True,
                    confidence="MEDIUM",
                    min_lot_size=2000,
                    note=f"Most of {suburb} has reticulated sewerage. Verify with Yarra Valley Water.",
                    verification_required=True,
                )
            elif status is False:
                return SewerageAssessment(
                    likely_sewered=False,
                    confidence="MEDIUM",
                    min_lot_size=4000,
                    note=f"{suburb} is typically unsewered. Check with water authority.",
                    verification_required=True,
                )
            else:  # "partial"
                return SewerageAssessment(
                    likely_sewered=None,
                    confidence="LOW",
                    min_lot_size=4000,  # Conservative assumption
                    note=f"{suburb} has partial sewerage coverage. MUST verify each property.",
                    verification_required=True,
                )

    # Unknown suburb
    return SewerageAssessment(
        likely_sewered=None,
        confidence="LOW",
        min_lot_size=4000,  # Conservative assumption
        note="Unknown sewerage status. Verify with water authority before purchase.",
        verification_required=True,
    )


# =============================================================================
# TRANSMISSION LINE ASSESSMENT
# =============================================================================

# Voltage to setback mapping (approximate Victorian guidelines)
TRANSMISSION_SETBACKS = {
    22: {"easement_width": 12, "building_setback": 5, "risk": "LOW"},
    66: {"easement_width": 25, "building_setback": 10, "risk": "MEDIUM"},
    132: {"easement_width": 35, "building_setback": 15, "risk": "HIGH"},
    220: {"easement_width": 45, "building_setback": 20, "risk": "HIGH"},
    330: {"easement_width": 55, "building_setback": 25, "risk": "HIGH"},
    500: {"easement_width": 70, "building_setback": 30, "risk": "CRITICAL"},
}


def get_transmission_setback(voltage_kv: int) -> dict:
    """Get transmission line setback requirements for voltage.

    Args:
        voltage_kv: Transmission line voltage in kV

    Returns:
        Dict with easement_width, building_setback, and risk level
    """
    # Find closest voltage tier
    for v in sorted(TRANSMISSION_SETBACKS.keys()):
        if voltage_kv <= v:
            return TRANSMISSION_SETBACKS[v]

    # Higher than 500kV - use maximum
    return TRANSMISSION_SETBACKS[500]


def assess_transmission_impact(
    voltage_kv: int,
    distance_m: float,
    land_size_sqm: float,
) -> dict[str, Any]:
    """Assess impact of nearby transmission line on development potential.

    Args:
        voltage_kv: Voltage of nearest transmission line
        distance_m: Distance to transmission line in meters
        land_size_sqm: Size of property in sqm

    Returns:
        Dict with impact assessment
    """
    setbacks = get_transmission_setback(voltage_kv)
    easement_width = setbacks["easement_width"]

    # Check if line is on or near property
    if distance_m <= easement_width / 2:
        # Line likely crosses property
        # Estimate unusable area (assume 100m length for rough calc)
        estimated_unusable = easement_width * 100
        usable_area = max(0, land_size_sqm - estimated_unusable)

        return {
            "impact": "CRITICAL",
            "reason": f"{voltage_kv}kV line likely crosses property",
            "estimated_unusable_sqm": estimated_unusable,
            "estimated_usable_sqm": usable_area,
            "recommendation": "Get survey to confirm easement location and size",
            "may_prevent_subdivision": usable_area < 4000,
        }
    elif distance_m <= easement_width:
        return {
            "impact": "HIGH",
            "reason": f"{voltage_kv}kV line easement may affect property edge",
            "recommendation": "Check title for registered easement",
            "may_prevent_subdivision": False,
        }
    elif distance_m <= 100:
        return {
            "impact": "LOW",
            "reason": f"{voltage_kv}kV line nearby but likely outside property",
            "recommendation": "Visual amenity consideration only",
            "may_prevent_subdivision": False,
        }
    else:
        return {
            "impact": "NONE",
            "reason": "No nearby transmission lines",
            "may_prevent_subdivision": False,
        }


# =============================================================================
# LDRZ SUBDIVISION ASSESSMENT (MAIN FUNCTION)
# =============================================================================


@dataclass
class LDRZAssessment:
    """Complete LDRZ subdivision assessment result."""

    is_ldrz: bool
    zone_code: str | None
    land_size_sqm: float

    # Sewerage
    sewerage: SewerageAssessment

    # Lot subdivision
    min_lot_size: int
    max_lots_possible: int
    subdividable: bool

    # Overlays
    overlay_assessment: OverlayAssessment

    # Transmission
    transmission_impact: dict | None

    # Overall
    feasible: bool
    reasons: list[str]
    warnings: list[str]
    next_steps: list[str]


def assess_ldrz_subdivision(
    lat: float,
    lon: float,
    land_size_sqm: float,
    suburb: str | None = None,
    transmission_info: dict | None = None,
) -> LDRZAssessment:
    """Perform complete LDRZ subdivision assessment.

    Args:
        lat: Latitude
        lon: Longitude
        land_size_sqm: Property size in square meters
        suburb: Suburb name (optional)
        transmission_info: Dict with voltage_kv and distance_m (from transmission check)

    Returns:
        LDRZAssessment with complete analysis
    """
    reasons = []
    warnings = []
    next_steps = []

    # 1. Check zone
    zones = get_zones_at_point(lat, lon)
    zone_code = zones[0]["code"] if zones else None
    is_ldrz = is_ldrz_zone(zone_code) if zone_code else False

    if not is_ldrz:
        reasons.append(f"Zone is {zone_code}, not LDRZ")

    # 2. Check sewerage
    sewerage = estimate_sewerage_availability(lat, lon, suburb)
    min_lot_size = sewerage.min_lot_size

    if sewerage.verification_required:
        next_steps.append("Call Yarra Valley Water (1300 304 688) to verify sewerage")

    # 3. Calculate lot potential
    if land_size_sqm >= min_lot_size * 2:
        max_lots = int(land_size_sqm // min_lot_size)
        subdividable = True
        if sewerage.likely_sewered:
            reasons.append(
                f"Can subdivide to {max_lots} × {min_lot_size}sqm lots (with sewer)"
            )
        else:
            warnings.append(
                f"If unsewered, can only create {int(land_size_sqm // 4000)} × 4000sqm lots"
            )
    elif land_size_sqm >= min_lot_size:
        max_lots = 1
        subdividable = False
        reasons.append(
            f"Land size ({land_size_sqm:.0f}sqm) below threshold for subdivision"
        )
    else:
        max_lots = 1
        subdividable = False
        reasons.append(
            f"Land too small for LDRZ ({land_size_sqm:.0f}sqm < {min_lot_size}sqm)"
        )

    # 4. Check overlays
    overlay_assessment = assess_overlays_for_subdivision(lat, lon)

    if overlay_assessment.high_risk_overlays:
        warnings.extend(overlay_assessment.notes)
        next_steps.append(
            "Pre-application meeting with council to discuss overlay impacts"
        )

    # 5. Transmission line impact
    transmission_impact = None
    if transmission_info:
        transmission_impact = assess_transmission_impact(
            transmission_info.get("voltage_kv", 0),
            transmission_info.get("distance_m", 1000),
            land_size_sqm,
        )
        if transmission_impact.get("may_prevent_subdivision"):
            warnings.append(
                f"Transmission line may prevent subdivision: {transmission_impact.get('reason')}"
            )

    # 6. Determine overall feasibility
    feasible = (
        is_ldrz
        and subdividable
        and overlay_assessment.can_subdivide
        and not (
            transmission_impact
            and transmission_impact.get("may_prevent_subdivision", False)
        )
    )

    if feasible:
        next_steps.extend(
            [
                "Get title search (LANDATA) to check covenants and easements",
                "Confirm frontage meets minimum requirements (~30m for 2 lots)",
                "Consider pre-application with Manningham Council",
            ]
        )

    return LDRZAssessment(
        is_ldrz=is_ldrz,
        zone_code=zone_code,
        land_size_sqm=land_size_sqm,
        sewerage=sewerage,
        min_lot_size=min_lot_size,
        max_lots_possible=max_lots,
        subdividable=subdividable,
        overlay_assessment=overlay_assessment,
        transmission_impact=transmission_impact,
        feasible=feasible,
        reasons=reasons,
        warnings=warnings,
        next_steps=next_steps,
    )


def print_ldrz_assessment(assessment: LDRZAssessment) -> None:
    """Print formatted LDRZ assessment to console."""
    console.print("\n[bold blue]═══ LDRZ SUBDIVISION ASSESSMENT ═══[/bold blue]\n")

    # Zone
    if assessment.is_ldrz:
        console.print(f"[green]✓ Zone: {assessment.zone_code} (LDRZ)[/green]")
    else:
        console.print(f"[red]✗ Zone: {assessment.zone_code} (Not LDRZ)[/red]")

    console.print(f"Land Size: {assessment.land_size_sqm:,.0f} sqm")

    # Sewerage
    console.print(f"\n[bold]Sewerage Status:[/bold]")
    if assessment.sewerage.likely_sewered:
        console.print(
            f"  [green]✓ Likely sewered[/green] → Min lot: {assessment.sewerage.min_lot_size}sqm"
        )
    elif assessment.sewerage.likely_sewered is False:
        console.print(
            f"  [red]✗ Likely unsewered[/red] → Min lot: {assessment.sewerage.min_lot_size}sqm"
        )
    else:
        console.print(
            f"  [yellow]? Unknown[/yellow] → Assume min lot: {assessment.sewerage.min_lot_size}sqm"
        )
    console.print(f"  [dim]{assessment.sewerage.note}[/dim]")

    # Subdivision potential
    console.print(f"\n[bold]Subdivision Potential:[/bold]")
    if assessment.subdividable:
        console.print(
            f"  [green]✓ Can create {assessment.max_lots_possible} lots[/green]"
        )
    else:
        console.print(
            f"  [red]✗ Cannot subdivide (need ≥{assessment.min_lot_size * 2}sqm)[/red]"
        )

    # Overlays
    if assessment.overlay_assessment.has_restrictions:
        console.print(f"\n[bold yellow]Overlay Restrictions:[/bold yellow]")
        for overlay in assessment.overlay_assessment.high_risk_overlays:
            console.print(f"  [red]⚠️ HIGH: {overlay}[/red]")
        for overlay in assessment.overlay_assessment.medium_risk_overlays:
            console.print(f"  [yellow]📋 MEDIUM: {overlay}[/yellow]")
    else:
        console.print(f"\n[green]✓ No restrictive overlays[/green]")

    # Transmission
    if assessment.transmission_impact:
        impact = assessment.transmission_impact
        if impact["impact"] in ("CRITICAL", "HIGH"):
            console.print(f"\n[red]⚡ Transmission Impact: {impact['impact']}[/red]")
            console.print(f"  {impact['reason']}")

    # Overall
    console.print(f"\n[bold]{'='*50}[/bold]")
    if assessment.feasible:
        console.print(f"[bold green]ASSESSMENT: SUBDIVISION FEASIBLE ✓[/bold green]")
    else:
        console.print(f"[bold red]ASSESSMENT: SUBDIVISION NOT FEASIBLE ✗[/bold red]")

    # Reasons
    if assessment.reasons:
        console.print(f"\n[bold]Notes:[/bold]")
        for reason in assessment.reasons:
            console.print(f"  • {reason}")

    if assessment.warnings:
        console.print(f"\n[bold yellow]Warnings:[/bold yellow]")
        for warning in assessment.warnings:
            console.print(f"  ⚠️ {warning}")

    # Next steps
    if assessment.next_steps:
        console.print(f"\n[bold cyan]Next Steps:[/bold cyan]")
        for i, step in enumerate(assessment.next_steps, 1):
            console.print(f"  {i}. {step}")
