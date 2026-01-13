"""Multi-strategy feasibility calculator.

Implements exhaustive property development strategies with Napier & Blakeley costings.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

console = Console()


# =============================================================================
# DEVELOPMENT STRATEGIES
# =============================================================================


class Strategy(Enum):
    """All property development strategies."""

    # Quick Flip / Value-Add
    LAND_BANK = "land_bank"  # Hold for appreciation
    COSMETIC_RENO = "cosmetic_reno"  # Paint, carpet, landscaping
    MAJOR_RENO = "major_reno"  # Kitchen, bathroom, structural

    # Single Dwelling
    KNOCKDOWN_REBUILD = "kdr"  # Demolish & build single new home
    EXTENSION = "extension"  # Add rooms to existing dwelling

    # Multi-Dwelling (Traditional)
    DUAL_OCC = "dual_occ"  # 2 dwellings (side-by-side or front-back)
    TOWNHOUSE_3 = "townhouse_3"  # 3 townhouses
    TOWNHOUSE_4_PLUS = "townhouse_4"  # 4+ townhouses

    # Subdivision
    SUBDIVIDE_RETAIN = "subdiv_retain"  # Subdivide, keep existing, sell rear
    SUBDIVIDE_SELL_LOTS = "subdiv_lots"  # Subdivide & sell vacant lots

    # Higher Density
    APARTMENT_3_STOREY = "apt_3"  # 3-storey walk-up apartments
    APARTMENT_4_PLUS = "apt_4"  # 4+ storey (lift required)

    # Specialist
    ROOMING_HOUSE = "rooming_house"  # Multiple rooms, shared facilities
    STUDENT_ACCOMMODATION = "student"  # Near university
    NDIS_SDA = "ndis_sda"  # Specialist Disability Accommodation
    CHILDCARE = "childcare"  # Childcare centre


@dataclass
class StrategyResult:
    """Result for a single strategy evaluation."""

    strategy: Strategy
    strategy_name: str
    is_applicable: bool  # Can this strategy be applied to the site?
    exclusion_reason: str  # Why not applicable (if any)

    # Yield
    dwellings: int
    gfa_sqm: float  # Gross Floor Area

    # Revenue
    sale_price_per_unit: float
    gdv: float  # Gross Development Value

    # Costs (N&B breakdown)
    land_cost: float
    demolition: float
    site_works: float
    construction: float
    professional_fees: float
    contingency: float
    statutory_costs: float
    finance_cost: float
    selling_costs: float
    tdc: float  # Total Development Cost

    # Profit
    profit: float
    margin_percent: float
    margin_on_cost: float  # ROC = Profit / TDC
    rlv: float  # Residual Land Value (max to pay for target margin)

    # Metrics
    cost_per_sqm_gfa: float
    profit_per_dwelling: float

    notes: list = field(default_factory=list)


@dataclass
class MultiStrategyResult:
    """Results from evaluating all strategies for a site."""

    site_address: str
    land_area_sqm: float
    frontage_m: float
    zone_code: str

    # All evaluated strategies
    strategies: list[StrategyResult] = field(default_factory=list)

    # Best options
    best_by_profit: Optional[StrategyResult] = None
    best_by_margin: Optional[StrategyResult] = None
    best_by_rlv: Optional[StrategyResult] = None

    def get_viable_strategies(self, min_margin: float = 15.0) -> list[StrategyResult]:
        """Get strategies meeting minimum margin threshold."""
        return [
            s
            for s in self.strategies
            if s.is_applicable and s.margin_percent >= min_margin
        ]


# =============================================================================
# STRATEGY APPLICABILITY RULES
# =============================================================================


def check_strategy_applicability(
    strategy: Strategy,
    land_area_sqm: float,
    frontage_m: float,
    zone_code: str,
    has_existing_dwelling: bool = True,
    slope_percent: float = 0.0,
    overlays: list[str] = None,
) -> tuple[bool, str]:
    """
    Check if a strategy can be applied to the site.
    Returns (is_applicable, reason_if_not).
    """
    overlays = overlays or []

    # Zone restrictions
    residential_zones = [
        "GRZ",
        "GRZ1",
        "GRZ2",
        "NRZ",
        "NRZ1",
        "NRZ2",
        "RGZ",
        "RGZ1",
        "MUZ",
        "TZ",
    ]
    base_zone = "".join(c for c in zone_code if not c.isdigit())

    # NRZ restrictions
    is_nrz = base_zone == "NRZ"
    nrz_max_dwellings = 2 if is_nrz else None

    rules = {
        Strategy.LAND_BANK: (True, ""),  # Always applicable
        Strategy.COSMETIC_RENO: (
            has_existing_dwelling,
            "No existing dwelling to renovate",
        ),
        Strategy.MAJOR_RENO: (
            has_existing_dwelling and land_area_sqm >= 300,
            "Need existing dwelling >= 300sqm land",
        ),
        Strategy.KNOCKDOWN_REBUILD: (
            land_area_sqm >= 400 and frontage_m >= 10,
            "Need >= 400sqm and 10m frontage",
        ),
        Strategy.EXTENSION: (
            has_existing_dwelling and land_area_sqm >= 400,
            "Need existing dwelling and space",
        ),
        Strategy.DUAL_OCC: (
            land_area_sqm >= 500 and frontage_m >= 15 and not is_nrz,
            (
                f"Need >= 500sqm, 15m frontage, not NRZ"
                if is_nrz
                else "Need >= 500sqm and 15m frontage"
            ),
        ),
        Strategy.TOWNHOUSE_3: (
            land_area_sqm >= 700 and frontage_m >= 18 and not is_nrz,
            "Need >= 700sqm, 18m frontage, not NRZ",
        ),
        Strategy.TOWNHOUSE_4_PLUS: (
            land_area_sqm >= 1000 and frontage_m >= 20 and not is_nrz,
            "Need >= 1000sqm, 20m frontage, not NRZ",
        ),
        Strategy.SUBDIVIDE_RETAIN: (
            land_area_sqm >= 800 and frontage_m >= 15,
            "Need >= 800sqm and 15m frontage",
        ),
        Strategy.SUBDIVIDE_SELL_LOTS: (
            land_area_sqm >= 1200 and frontage_m >= 20,
            "Need >= 1200sqm and 20m frontage for 3+ lots",
        ),
        Strategy.APARTMENT_3_STOREY: (
            land_area_sqm >= 800
            and frontage_m >= 20
            and base_zone in ["GRZ", "RGZ", "MUZ"],
            "Need >= 800sqm, 20m frontage, GRZ/RGZ/MUZ zone",
        ),
        Strategy.APARTMENT_4_PLUS: (
            land_area_sqm >= 1500
            and frontage_m >= 25
            and base_zone in ["RGZ", "MUZ", "TZ"],
            "Need >= 1500sqm, 25m frontage, RGZ/MUZ/TZ zone",
        ),
        Strategy.ROOMING_HOUSE: (
            land_area_sqm >= 400 and base_zone in ["GRZ", "RGZ", "MUZ"],
            "Need >= 400sqm in GRZ/RGZ/MUZ",
        ),
        Strategy.STUDENT_ACCOMMODATION: (
            land_area_sqm >= 600,  # Would need proximity check to uni
            "Need >= 600sqm (proximity to university not checked)",
        ),
        Strategy.NDIS_SDA: (
            land_area_sqm >= 500 and slope_percent < 5,
            "Need >= 500sqm, flat site (<5% slope)",
        ),
        Strategy.CHILDCARE: (
            land_area_sqm >= 1500
            and frontage_m >= 25
            and base_zone in ["GRZ", "MUZ", "C1Z", "C2Z"],
            "Need >= 1500sqm, 25m frontage, appropriate zone",
        ),
    }

    if strategy in rules:
        is_ok, reason = rules[strategy]
        # Additional slope check for multi-dwelling
        if (
            is_ok
            and slope_percent > 12
            and strategy
            in [
                Strategy.TOWNHOUSE_3,
                Strategy.TOWNHOUSE_4_PLUS,
                Strategy.APARTMENT_3_STOREY,
                Strategy.APARTMENT_4_PLUS,
            ]
        ):
            return False, f"Slope too steep ({slope_percent:.0f}%) for multi-dwelling"
        return is_ok, reason

    return True, ""


# =============================================================================
# COST CALCULATIONS (NAPIER & BLAKELEY)
# =============================================================================

_nb_costs: dict = None


def _load_nb_costs() -> dict:
    """Load N&B cost data."""
    global _nb_costs
    if _nb_costs is None:
        cost_file = (
            Path(__file__).parent.parent.parent / "config" / "construction_costs.yaml"
        )
        if cost_file.exists():
            with open(cost_file, "r", encoding="utf-8") as f:
                _nb_costs = yaml.safe_load(f) or {}
        else:
            _nb_costs = {}
    return _nb_costs


def get_nb_rate(category: str, level: str = "medium") -> float:
    """Get N&B rate for category/level."""
    costs = _load_nb_costs()
    return costs.get(category, {}).get(level, 2525)


# Strategy-specific parameters
STRATEGY_PARAMS = {
    Strategy.LAND_BANK: {
        "build": False,
        "holding_months": 24,
        "appreciation_pa": 0.05,
    },
    Strategy.COSMETIC_RENO: {
        "build_type": "RENOVATION",
        "quality": "cosmetic",
        "gfa_factor": 0,  # No new GFA
        "reno_sqm": 150,  # Typical reno area
        "value_uplift": 1.15,
    },
    Strategy.MAJOR_RENO: {
        "build_type": "RENOVATION",
        "quality": "major",
        "gfa_factor": 0,
        "reno_sqm": 180,
        "value_uplift": 1.30,
    },
    Strategy.KNOCKDOWN_REBUILD: {
        "build_type": "SINGLE_DWELLING",
        "quality": "medium",
        "dwellings": 1,
        "gfa_per_dwelling": 250,
        "demolition": True,
    },
    Strategy.EXTENSION: {
        "build_type": "SINGLE_DWELLING",
        "quality": "medium",
        "extension_sqm": 80,
        "value_uplift": 1.25,
    },
    Strategy.DUAL_OCC: {
        "build_type": "TOWNHOUSE",
        "quality": "medium",
        "dwellings": 2,
        "gfa_per_dwelling": 180,
        "demolition": True,
    },
    Strategy.TOWNHOUSE_3: {
        "build_type": "TOWNHOUSE",
        "quality": "medium",
        "dwellings": 3,
        "gfa_per_dwelling": 160,
        "demolition": True,
    },
    Strategy.TOWNHOUSE_4_PLUS: {
        "build_type": "TOWNHOUSE",
        "quality": "medium",
        "dwellings": 4,  # Will calculate based on land
        "gfa_per_dwelling": 140,
        "demolition": True,
    },
    Strategy.SUBDIVIDE_RETAIN: {
        "build_type": None,  # No construction
        "lots": 2,
        "demolition": False,
    },
    Strategy.SUBDIVIDE_SELL_LOTS: {
        "build_type": None,
        "lots_per_1000sqm": 2.5,
        "demolition": True,
    },
    Strategy.APARTMENT_3_STOREY: {
        "build_type": "APARTMENT",
        "quality": "medium",
        "dwellings_per_1000sqm": 12,  # Approx
        "gfa_per_dwelling": 75,
        "demolition": True,
    },
    Strategy.APARTMENT_4_PLUS: {
        "build_type": "APARTMENT",
        "quality": "high",
        "dwellings_per_1000sqm": 20,
        "gfa_per_dwelling": 70,
        "demolition": True,
    },
    Strategy.ROOMING_HOUSE: {
        "build_type": "TOWNHOUSE",  # Similar construction
        "quality": "budget",
        "rooms_per_100sqm_land": 3,
        "gfa_per_room": 20,
        "demolition": True,
    },
    Strategy.NDIS_SDA: {
        "build_type": "SINGLE_DWELLING",
        "quality": "high",  # Accessibility requirements
        "dwellings": 1,
        "gfa_per_dwelling": 200,
        "sda_premium": 1.3,  # 30% premium for SDA compliance
    },
    Strategy.CHILDCARE: {
        "build_type": "APARTMENT",  # Commercial-style
        "quality": "high",
        "gfa_sqm": 600,  # Typical 75-place centre
        "places": 75,
    },
}

# Suburb sale prices (per dwelling/unit) - should be updated with market data
SUBURB_PRICES = {
    "default": {
        "house": 1_200_000,
        "townhouse": 950_000,
        "apartment": 650_000,
        "land_per_sqm": 1_500,
        "room_weekly": 250,
    },
    "donvale": {
        "house": 1_400_000,
        "townhouse": 1_100_000,
        "apartment": 750_000,
        "land_per_sqm": 1_800,
        "room_weekly": 280,
    },
}


def calculate_strategy(
    strategy: Strategy,
    land_price: float,
    land_area_sqm: float,
    frontage_m: float,
    zone_code: str,
    suburb: str = "default",
    has_existing_dwelling: bool = True,
    existing_value: float = 0,
    slope_percent: float = 0,
) -> StrategyResult:
    """
    Calculate full feasibility for a single strategy.
    """
    params = STRATEGY_PARAMS.get(strategy, {})
    prices = SUBURB_PRICES.get(suburb.lower(), SUBURB_PRICES["default"])

    # Check applicability
    is_applicable, exclusion = check_strategy_applicability(
        strategy,
        land_area_sqm,
        frontage_m,
        zone_code,
        has_existing_dwelling,
        slope_percent,
    )

    # Initialize result with zeros
    result = StrategyResult(
        strategy=strategy,
        strategy_name=strategy.value.replace("_", " ").title(),
        is_applicable=is_applicable,
        exclusion_reason=exclusion,
        dwellings=0,
        gfa_sqm=0,
        sale_price_per_unit=0,
        gdv=0,
        land_cost=land_price,
        demolition=0,
        site_works=0,
        construction=0,
        professional_fees=0,
        contingency=0,
        statutory_costs=0,
        finance_cost=0,
        selling_costs=0,
        tdc=land_price,
        profit=0,
        margin_percent=0,
        margin_on_cost=0,
        rlv=0,
        cost_per_sqm_gfa=0,
        profit_per_dwelling=0,
    )

    if not is_applicable:
        return result

    # Calculate based on strategy type
    notes = []

    # --- LAND BANK ---
    if strategy == Strategy.LAND_BANK:
        appreciation = params["appreciation_pa"]
        months = params["holding_months"]
        result.gdv = land_price * (1 + appreciation * months / 12)
        result.tdc = land_price * 1.05  # Holding costs
        result.profit = result.gdv - result.tdc

    # --- RENOVATION ---
    elif strategy in [Strategy.COSMETIC_RENO, Strategy.MAJOR_RENO]:
        reno_sqm = params.get("reno_sqm", 150)
        reno_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = reno_sqm * reno_rate
        result.professional_fees = result.construction * 0.05
        result.contingency = result.construction * 0.10
        existing = existing_value or land_price * 0.7
        result.gdv = existing * params["value_uplift"] + land_price * 0.3
        result.gfa_sqm = reno_sqm
        result.dwellings = 1

    # --- KNOCKDOWN REBUILD ---
    elif strategy == Strategy.KNOCKDOWN_REBUILD:
        result.dwellings = 1
        result.gfa_sqm = params["gfa_per_dwelling"]
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate
        result.demolition = 120 * 150  # 150sqm existing
        result.site_works = result.construction * (0.08 if slope_percent < 5 else 0.15)
        result.gdv = prices["house"]
        result.sale_price_per_unit = prices["house"]

    # --- DUAL OCC / TOWNHOUSE ---
    elif strategy in [
        Strategy.DUAL_OCC,
        Strategy.TOWNHOUSE_3,
        Strategy.TOWNHOUSE_4_PLUS,
    ]:
        if strategy == Strategy.TOWNHOUSE_4_PLUS:
            # Calculate dwellings based on land
            result.dwellings = min(int(land_area_sqm / 250), 6)
        else:
            result.dwellings = params["dwellings"]

        result.gfa_sqm = result.dwellings * params["gfa_per_dwelling"]
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate
        result.demolition = 120 * 150 if params.get("demolition") else 0
        result.site_works = result.construction * (0.08 if slope_percent < 5 else 0.15)
        result.sale_price_per_unit = prices["townhouse"]
        result.gdv = result.dwellings * result.sale_price_per_unit

    # --- SUBDIVISION ---
    elif strategy in [Strategy.SUBDIVIDE_RETAIN, Strategy.SUBDIVIDE_SELL_LOTS]:
        if strategy == Strategy.SUBDIVIDE_RETAIN:
            lots = 2
            result.gdv = prices["land_per_sqm"] * (land_area_sqm * 0.4) + existing_value
            result.dwellings = 1  # Retain existing
        else:
            lots = int(land_area_sqm / 400)
            result.gdv = lots * prices["land_per_sqm"] * 400
            result.demolition = 120 * 150
            result.dwellings = 0

        result.statutory_costs = lots * 35000  # Subdivision costs
        result.construction = 0
        notes.append(f"{lots} lots")

    # --- APARTMENTS ---
    elif strategy in [Strategy.APARTMENT_3_STOREY, Strategy.APARTMENT_4_PLUS]:
        result.dwellings = int(land_area_sqm * params["dwellings_per_1000sqm"] / 1000)
        result.gfa_sqm = result.dwellings * params["gfa_per_dwelling"]
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate
        result.demolition = 120 * 200
        result.site_works = result.construction * 0.12  # More complex site works
        result.sale_price_per_unit = prices["apartment"]
        result.gdv = result.dwellings * result.sale_price_per_unit

    # --- ROOMING HOUSE ---
    elif strategy == Strategy.ROOMING_HOUSE:
        rooms = int(land_area_sqm * params["rooms_per_100sqm_land"] / 100)
        result.dwellings = rooms  # Rooms as "units"
        result.gfa_sqm = rooms * params["gfa_per_room"] * 3  # Common areas
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate
        result.demolition = 120 * 150
        # GDV based on rental yield cap (7% yield)
        weekly_rent = rooms * prices["room_weekly"]
        annual_rent = weekly_rent * 52
        result.gdv = annual_rent / 0.07  # 7% cap rate
        notes.append(f"{rooms} rooms @ ${prices['room_weekly']}/wk")

    # --- NDIS SDA ---
    elif strategy == Strategy.NDIS_SDA:
        result.dwellings = 1
        result.gfa_sqm = params["gfa_per_dwelling"]
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate * params["sda_premium"]
        result.demolition = 120 * 150
        # SDA payments are significantly higher - cap rate approach
        annual_sda_payment = 150_000  # Typical HPS SDA
        result.gdv = annual_sda_payment / 0.08  # 8% cap
        notes.append("SDA High Physical Support")

    # --- CHILDCARE ---
    elif strategy == Strategy.CHILDCARE:
        result.gfa_sqm = params["gfa_sqm"]
        build_rate = get_nb_rate(params["build_type"], params["quality"])
        result.construction = result.gfa_sqm * build_rate * 1.2  # Commercial premium
        result.demolition = 120 * 200
        result.site_works = result.construction * 0.15  # Outdoor areas
        # Childcare valued on cap rate
        annual_rent = params["places"] * 350 * 52 * 0.15  # 15% of fees
        result.gdv = annual_rent / 0.055  # 5.5% cap
        notes.append(f"{params['places']} place centre")

    # --- COMMON COSTS ---
    if result.construction > 0:
        result.professional_fees = result.construction * 0.10
        result.contingency = result.construction * 0.075

    result.statutory_costs += (result.construction + result.demolition) * 0.02

    # Finance cost (draw-down adjusted)
    total_capital = result.land_cost + result.demolition + result.construction
    result.finance_cost = total_capital * 0.07 * (14 / 12) * 0.6  # 60% avg draw

    # Selling costs (agent fees 1.5%)
    result.selling_costs = result.gdv * 0.015

    # TDC
    result.tdc = (
        result.land_cost
        + result.demolition
        + result.site_works
        + result.construction
        + result.professional_fees
        + result.contingency
        + result.statutory_costs
        + result.finance_cost
        + result.selling_costs
    )

    # GST (margin scheme)
    gst = (result.gdv - result.land_cost) / 11 if result.gdv > result.land_cost else 0

    # Profit
    result.profit = result.gdv - result.tdc - gst
    result.margin_percent = (result.profit / result.tdc * 100) if result.tdc > 0 else 0
    result.margin_on_cost = (
        (result.profit / (result.tdc - result.land_cost) * 100)
        if (result.tdc - result.land_cost) > 0
        else 0
    )

    # RLV (target 20% margin)
    target_margin = 0.20
    if result.gdv > 0 and (result.tdc - result.land_cost) > 0:
        other_costs = result.tdc - result.land_cost
        result.rlv = (result.gdv / (1 + target_margin)) - other_costs

    # Per-unit metrics
    if result.gfa_sqm > 0:
        result.cost_per_sqm_gfa = (result.tdc - result.land_cost) / result.gfa_sqm
    if result.dwellings > 0:
        result.profit_per_dwelling = result.profit / result.dwellings

    result.notes = notes
    return result


def evaluate_all_strategies(
    land_price: float,
    land_area_sqm: float,
    frontage_m: float,
    zone_code: str,
    suburb: str = "default",
    address: str = "",
    has_existing_dwelling: bool = True,
    existing_value: float = 0,
    slope_percent: float = 0,
) -> MultiStrategyResult:
    """
    Evaluate ALL strategies for a site and return ranked results.
    """
    result = MultiStrategyResult(
        site_address=address,
        land_area_sqm=land_area_sqm,
        frontage_m=frontage_m,
        zone_code=zone_code,
    )

    for strategy in Strategy:
        strat_result = calculate_strategy(
            strategy=strategy,
            land_price=land_price,
            land_area_sqm=land_area_sqm,
            frontage_m=frontage_m,
            zone_code=zone_code,
            suburb=suburb,
            has_existing_dwelling=has_existing_dwelling,
            existing_value=existing_value,
            slope_percent=slope_percent,
        )
        result.strategies.append(strat_result)

    # Find best options
    viable = [s for s in result.strategies if s.is_applicable and s.profit > 0]

    if viable:
        result.best_by_profit = max(viable, key=lambda s: s.profit)
        result.best_by_margin = max(viable, key=lambda s: s.margin_percent)
        result.best_by_rlv = max(viable, key=lambda s: s.rlv)

    return result


def print_strategy_summary(result: MultiStrategyResult) -> None:
    """Print formatted summary of all strategies."""
    console.print(f"\n[bold]Multi-Strategy Analysis: {result.site_address}[/bold]")
    console.print(
        f"Land: {result.land_area_sqm:.0f}sqm | Frontage: {result.frontage_m:.1f}m | Zone: {result.zone_code}\n"
    )

    console.print("[bold]Viable Strategies:[/bold]")
    console.print("-" * 80)

    viable = result.get_viable_strategies(min_margin=10)

    for s in sorted(viable, key=lambda x: -x.profit):
        emoji = (
            "🟢" if s.margin_percent >= 20 else "🟡" if s.margin_percent >= 15 else "🟠"
        )
        console.print(
            f"{emoji} [bold]{s.strategy_name:20}[/bold] | "
            f"Dwellings: {s.dwellings:2} | "
            f"GDV: ${s.gdv/1e6:.2f}M | "
            f"TDC: ${s.tdc/1e6:.2f}M | "
            f"Profit: ${s.profit/1e6:.2f}M | "
            f"Margin: {s.margin_percent:.1f}%"
        )

    if result.best_by_profit:
        console.print(
            f"\n[green]Best by Profit: {result.best_by_profit.strategy_name} (${result.best_by_profit.profit/1e6:.2f}M)[/green]"
        )
    if result.best_by_margin:
        console.print(
            f"[green]Best by Margin: {result.best_by_margin.strategy_name} ({result.best_by_margin.margin_percent:.1f}%)[/green]"
        )
