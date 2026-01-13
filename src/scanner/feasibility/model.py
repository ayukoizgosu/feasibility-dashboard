"""Feasibility model for development scoring."""

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.models import FeasibilityRun, Site, SiteConstraint

console = Console()


# =============================================================================
# NAPIER & BLAKELEY CONSTRUCTION COST LOADER
# =============================================================================

_construction_costs: dict = None


def get_construction_costs() -> dict:
    """Load Napier & Blakeley construction cost data from YAML."""
    global _construction_costs
    if _construction_costs is None:
        cost_file = (
            Path(__file__).parent.parent.parent.parent
            / "config"
            / "construction_costs.yaml"
        )
        if cost_file.exists():
            with open(cost_file, "r", encoding="utf-8") as f:
                _construction_costs = yaml.safe_load(f) or {}
        else:
            console.print(
                "[yellow]Warning: construction_costs.yaml not found, using defaults[/yellow]"
            )
            _construction_costs = {}
    return _construction_costs


def get_build_cost(building_type: str = "TOWNHOUSE", quality: str = "medium") -> float:
    """Get construction cost per sqm from N&B data.

    Args:
        building_type: SINGLE_DWELLING, TOWNHOUSE, APARTMENT, RENOVATION
        quality: budget, medium, high, premium

    Returns:
        Cost per sqm (AUD)
    """
    costs = get_construction_costs()
    type_costs = costs.get(building_type, {})
    return type_costs.get(quality, 2525.0)  # Default to N&B townhouse medium


@dataclass
class FeasibilityResult:
    strategy: str  # "Renovate" or "DualOcc"
    gdv: float
    tdc: float
    margin_dollars: float
    margin_percent: float
    rlv: float  # Residual Land Value (Max purchase price for target margin)
    is_viable: bool  # Margin >= 20%
    notes: list[str]


@dataclass
class SimpleFeasibilityConfig:
    """Configuration based on Napier & Blakeley datacards."""

    # Construction (N&B 2024 Melbourne rates)
    build_cost_per_sqm: float = 2525.0  # N&B Townhouse Medium
    building_type: str = "TOWNHOUSE"  # SINGLE_DWELLING, TOWNHOUSE, APARTMENT
    quality: str = "medium"  # budget, medium, high, premium

    # Professional fees (N&B typical combined)
    prof_fees_percent: float = 0.10  # 10% combined (arch + eng + PM)
    contingency_percent: float = 0.075  # 7.5% at tender stage

    # Finance & holding
    interest_rate: float = 0.07
    holding_period_months: int = 14  # N&B typical for townhouse

    # Sales & statutory
    selling_costs_percent: float = 0.015  # Agent fees (1.5%)
    gst_rate: float = 0.10
    statutory_percent: float = 0.02  # Council + Building permits

    # Site works
    site_works_percent: float = 0.08  # Standard site (N&B)

    def __post_init__(self):
        """Load actual N&B rate based on building type and quality."""
        self.build_cost_per_sqm = get_build_cost(self.building_type, self.quality)


def calculate_simple_feasibility(
    land_price: float,
    land_area_sqm: float,
    strategy: str = "DualOcc",
    config: SimpleFeasibilityConfig = SimpleFeasibilityConfig(),
    max_footprint_sqm: float = None,
    max_dwellings: int = None,
) -> FeasibilityResult:
    """
    Back-of-napkin calculation (User Framework Phase 4 & 9).
    """
    notes = []

    # Check max dwellings constraint
    if max_dwellings and max_dwellings < 2 and strategy == "DualOcc":
        strategy = "Single"
        notes.append(f"Downgraded to Single (Zone caps dwellings at {max_dwellings})")

    # 1. Estimate Yield
    if strategy == "DualOcc":
        # Target 220sqm, but limited by land area availability
        # Available buildable land = land_area * site_coverage (approx via max_footprint)
        max_ground_floor = (
            max_footprint_sqm if max_footprint_sqm else (land_area_sqm * 0.6)
        )

        # Assume 2 stories -> Total floor area approx 1.8x ground floor (some upper setback)
        max_total_area = max_ground_floor * 1.8

        # Calculate max area per dwelling (2 dwellings)
        max_dwelling_size = max_total_area / 2

        dwelling_size_sqm = min(220, max_dwelling_size)
        total_build_area_sqm = dwelling_size_sqm * 2

        if max_footprint_sqm and (total_build_area_sqm / 1.8) > max_footprint_sqm:
            notes.append(
                f"Size Constrained by Zone Coverage: {dwelling_size_sqm:.0f}m2"
            )

        # Determine GDV (Placeholder logic)
        # Using fixed $1.2M for now (need Suburb stats later)
        sales_price_per_unit = 1_200_000
        gdv = sales_price_per_unit * 2
    else:
        # Single dwelling logic
        total_build_area_sqm = 0
        gdv = land_price * 1.2

    # 2. TDC
    construction_cost = total_build_area_sqm * config.build_cost_per_sqm
    prof_fees = construction_cost * config.prof_fees_percent
    contingency = construction_cost * config.contingency_percent
    statutory_costs = 0.05 * land_price
    finance_cost = (
        (land_price + construction_cost)
        * config.interest_rate
        * (config.holding_period_months / 12)
        * 0.6
    )
    selling_costs = gdv * config.selling_costs_percent

    tdc = (
        land_price
        + statutory_costs
        + construction_cost
        + prof_fees
        + contingency
        + finance_cost
        + selling_costs
    )

    # 3. Margin
    gst_payable = (gdv - land_price) / 11
    net_profit = gdv - tdc - gst_payable
    margin_percent = (net_profit / tdc) * 100 if tdc > 0 else 0

    return FeasibilityResult(
        strategy=strategy,
        gdv=gdv,
        tdc=tdc,
        margin_dollars=net_profit,
        margin_percent=margin_percent,
        rlv=0.0,
        is_viable=margin_percent >= 20.0,
        notes=notes + [f"Strategy: {strategy}", f"Margin: {margin_percent:.1f}%"],
    )


# Sale price estimates by suburb (AUD per dwelling)
# These are rough estimates - should be updated with market data
SUBURB_SALE_PRICES = {
    # Inner-Middle Ring
    "reservoir": 850000,
    "preston": 950000,
    "coburg": 1000000,
    "thornbury": 1050000,
    # Middle Ring
    "glenroy": 750000,
    "fawkner": 700000,
    "heidelberg west": 800000,
    "pascoe vale": 850000,
    # Outer Growth
    "campbellfield": 600000,
    "broadmeadows": 600000,
    "sunshine west": 700000,
    "st albans": 650000,
}

DEFAULT_SALE_PRICE = 750000  # Fallback


def estimate_yield(
    land_area_m2: float, zone_code: str, config
) -> tuple[int, int, int, float]:
    """Estimate dwelling yield from land area and zone.

    Returns: (low, base, high, confidence)
    """
    if not land_area_m2 or land_area_m2 < 300:
        return 1, 1, 1, 0.5

    zone_params = config.get_zone_params(zone_code or "GRZ1")
    yield_factor = zone_params.yield_factor

    # Check for max dwellings cap (e.g., NRZ)
    max_dwellings = zone_params.max_dwellings

    # Calculate base yield
    base_yield = land_area_m2 * yield_factor

    # Apply realistic minimums
    base_yield = max(1, base_yield)

    # Apply max if zone limits
    if max_dwellings:
        base_yield = min(base_yield, max_dwellings)

    # Calculate range
    low = max(1, int(base_yield * 0.8))
    base = max(1, int(base_yield))
    high = int(base_yield * 1.2)

    if max_dwellings:
        high = min(high, max_dwellings)

    # Confidence based on land size reliability
    confidence = 0.7 if land_area_m2 > 400 else 0.5

    return low, base, high, confidence


def calculate_feasibility(
    site: Site, constraints: list[SiteConstraint], config
) -> FeasibilityRun:
    """Calculate feasibility for a site.

    Returns: FeasibilityRun object
    """
    feas = config.feasibility

    # Get land area (prefer parcel data, fallback to listing)
    land_area = site.land_area_m2 or site.land_size_listed or 500

    # Get zone from constraints
    zone_code = "GRZ1"  # Default
    for c in constraints:
        if c.constraint_type == "zone":
            zone_code = c.code
            break

    # Estimate yield
    dwellings_low, dwellings_base, dwellings_high, yield_conf = estimate_yield(
        land_area, zone_code, config
    )

    # Land cost (use price guide or mid-range)
    land_cost = site.price_guide
    if not land_cost and site.price_low and site.price_high:
        land_cost = (site.price_low + site.price_high) / 2
    if not land_cost:
        land_cost = 1000000  # Default assumption

    # Sale price per dwelling
    suburb_key = (site.suburb or "").lower().strip()
    sale_price = SUBURB_SALE_PRICES.get(suburb_key, DEFAULT_SALE_PRICE)

    # Build costs
    gfa_per_dwelling = feas.avg_dwelling_size_m2
    total_gfa = dwellings_base * gfa_per_dwelling
    build_cost = total_gfa * feas.build_cost_per_m2

    # Additional costs
    soft_costs = build_cost * feas.soft_cost_pct
    contingency = (build_cost + soft_costs) * feas.contingency_pct

    # Holding costs (interest on land + build over holding period)
    avg_capital = land_cost + (build_cost + soft_costs + contingency) / 2
    holding_costs = avg_capital * feas.finance_rate * (feas.holding_months / 12)

    # Revenue
    revenue_base = dwellings_base * sale_price
    revenue_low = dwellings_low * sale_price * 0.95  # Slight discount
    revenue_high = dwellings_high * sale_price * 1.05  # Slight premium

    # Selling costs
    selling_costs = revenue_base * feas.selling_cost_pct

    # Total costs
    total_cost_base = (
        land_cost
        + build_cost
        + soft_costs
        + contingency
        + holding_costs
        + selling_costs
    )
    total_cost_low = total_cost_base * 1.1  # 10% cost blowout scenario
    total_cost_high = total_cost_base * 0.95  # Optimistic

    # Profit
    profit_base = revenue_base - total_cost_base
    profit_low = revenue_low - total_cost_low
    profit_high = revenue_high - total_cost_high

    # Margin
    margin_base = profit_base / revenue_base if revenue_base > 0 else 0

    # Calculate score
    # Factors: margin, yield confidence, constraint severity
    max_severity = max((c.severity for c in constraints), default=0)
    severity_penalty = max_severity * 0.15  # 15% penalty per severity level

    score = margin_base * yield_conf * (1 - severity_penalty)

    # Boost for larger lots (more development potential)
    if land_area > 800:
        score *= 1.1
    if land_area > 1000:
        score *= 1.1

    # Penalty for very small margins
    if margin_base < 0.15:
        score *= 0.5

    return FeasibilityRun(
        id=str(uuid.uuid4()),
        site_id=site.id,
        assumptions={
            "zone": zone_code,
            "land_area_m2": land_area,
            "build_cost_per_m2": feas.build_cost_per_m2,
            "sale_price_per_dwelling": sale_price,
            "holding_months": feas.holding_months,
        },
        dwellings_low=dwellings_low,
        dwellings_base=dwellings_base,
        dwellings_high=dwellings_high,
        yield_confidence=yield_conf,
        land_cost=land_cost,
        build_cost=build_cost,
        soft_costs=soft_costs,
        contingency=contingency,
        holding_costs=holding_costs,
        selling_costs=selling_costs,
        total_cost_low=total_cost_low,
        total_cost_base=total_cost_base,
        total_cost_high=total_cost_high,
        sale_price_per_dwelling=sale_price,
        revenue_low=revenue_low,
        revenue_base=revenue_base,
        revenue_high=revenue_high,
        profit_low=profit_low,
        profit_base=profit_base,
        profit_high=profit_high,
        margin_base=margin_base,
        score=score,
    )


def run_feasibility() -> int:
    """Run feasibility analysis for all sites."""
    config = get_config()
    analyzed = 0

    with get_session() as session:
        # Get sites with geocoding complete
        sites = (
            session.query(Site)
            .filter(Site.lat.isnot(None), Site.geocode_status == "success")
            .all()
        )

        if not sites:
            console.print("[yellow]No sites to analyze[/yellow]")
            return 0

        console.print(f"[blue]Running feasibility for {len(sites)} sites...[/blue]")

        for i, site in enumerate(sites):
            # Get constraints for site
            constraints = session.query(SiteConstraint).filter_by(site_id=site.id).all()

            # Clear previous runs
            session.query(FeasibilityRun).filter_by(site_id=site.id).delete()

            # Calculate feasibility
            run = calculate_feasibility(site, constraints, config)
            session.add(run)

            analyzed += 1

            if (i + 1) % 100 == 0:
                console.print(f"  Progress: {i + 1}/{len(sites)}")
                session.commit()

    console.print(f"[green]Feasibility complete for {analyzed} sites[/green]")
    return analyzed


def run():
    """Entry point."""
    run_feasibility()


if __name__ == "__main__":
    run()
