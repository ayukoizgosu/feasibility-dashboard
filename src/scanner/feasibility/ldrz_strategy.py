"""LDRZ Subdivision Feasibility Calculator.

Calculates profitability of subdividing LDRZ blocks into smaller lots,
without construction (land-only subdivision).
"""

from dataclasses import dataclass

from rich.console import Console

console = Console()


# =============================================================================
# LDRZ COST PARAMETERS
# =============================================================================

# Stamp duty rates (Victorian 2024)
STAMP_DUTY_RATES = [
    (25000, 0.014),  # 0-25,000: 1.4%
    (130000, 0.024),  # 25,001-130,000: 2.4%
    (960000, 0.05),  # 130,001-960,000: 5%
    (2000000, 0.055),  # 960,001-2,000,000: 5.5%
    (float("inf"), 0.065),  # 2,000,000+: 6.5%
]


def calculate_stamp_duty(purchase_price: float) -> float:
    """Calculate Victorian stamp duty.

    Args:
        purchase_price: Property purchase price

    Returns:
        Stamp duty amount
    """
    duty = 0
    remaining = purchase_price
    prev_threshold = 0

    for threshold, rate in STAMP_DUTY_RATES:
        if remaining <= 0:
            break
        taxable = min(remaining, threshold - prev_threshold)
        duty += taxable * rate
        remaining -= taxable
        prev_threshold = threshold

    return duty


# LDRZ Subdivision costs (Melbourne 2024-2025)
SUBDIVISION_COSTS = {
    "town_planner": 5000,
    "surveyor": 8000,
    "council_fees": 3000,
    "plan_certification": 2000,
    "titles_office": 1500,
    "sewer_connection": 15000,  # If needed for new lot
    "power_connection": 5000,
    "crossover": 8000,  # Per new driveway
    "fencing": 80,  # Per linear meter
}

# Finance assumptions
DEFAULT_INTEREST_RATE = 0.065  # 6.5% p.a.
DEFAULT_LVR = 0.80  # 80% LVR

# Sale costs
AGENT_COMMISSION = 0.015  # 1.5%
MARKETING_PER_LOT = 3000


@dataclass
class LDRZFeasibility:
    """LDRZ subdivision feasibility result."""

    # Inputs
    purchase_price: float
    land_size_sqm: float
    num_lots: int
    min_lot_size: int

    # Costs
    stamp_duty: float
    legals: float
    subdivision_costs: float
    finance_cost: float
    selling_costs: float
    total_costs: float

    # Revenue
    price_per_lot: float
    gdv: float
    gst: float

    # Profit
    gross_profit: float
    net_profit: float
    margin_percent: float

    # ROE
    cash_required: float
    total_roe: float
    annualized_roe: float

    # Timeline
    holding_months: int

    # Viability
    is_viable: bool
    notes: list[str]


def estimate_lot_value(
    suburb: str,
    lot_size_sqm: float,
    original_land_rate: float | None = None,
) -> float:
    """Estimate sale value for subdivided LDRZ lot.

    Uses either suburb-specific rates or markup from original purchase.

    Args:
        suburb: Suburb name
        lot_size_sqm: Size of lot in sqm
        original_land_rate: Original purchase price per sqm (optional)

    Returns:
        Estimated sale price for lot
    """
    # Default rates by suburb (2024-2025 estimates)
    SUBURB_RATES = {
        "donvale": 600,
        "templestowe": 700,
        "park orchards": 550,
        "warrandyte": 500,
        "wonga park": 450,
        "eltham": 500,
        "eltham north": 450,
        "research": 400,
        "chirnside park": 500,
        "montrose": 400,
        "mount evelyn": 350,
    }

    suburb_lower = suburb.lower().strip() if suburb else ""

    if suburb_lower in SUBURB_RATES:
        rate = SUBURB_RATES[suburb_lower]
    elif original_land_rate:
        # Assume 25% markup for subdivided lots (smaller lots = higher rate)
        rate = original_land_rate * 1.25
    else:
        # Default conservative rate
        rate = 500

    return lot_size_sqm * rate


def calculate_ldrz_feasibility(
    purchase_price: float,
    land_size_sqm: float,
    has_sewerage: bool = True,
    suburb: str | None = None,
    holding_months: int = 12,
    interest_rate: float = DEFAULT_INTEREST_RATE,
    lvr: float = DEFAULT_LVR,
) -> LDRZFeasibility:
    """Calculate LDRZ subdivision feasibility.

    Args:
        purchase_price: Property purchase price
        land_size_sqm: Total land size in sqm
        has_sewerage: Whether property has reticulated sewerage
        suburb: Suburb name (for lot value estimation)
        holding_months: Expected holding period in months
        interest_rate: Annual interest rate
        lvr: Loan to value ratio

    Returns:
        LDRZFeasibility with complete analysis
    """
    notes = []

    # 1. Determine minimum lot size and number of lots
    min_lot_size = 2000 if has_sewerage else 4000
    num_lots = int(land_size_sqm // min_lot_size)

    if num_lots < 2:
        notes.append("Cannot subdivide - land too small")
        num_lots = 1

    actual_lot_size = land_size_sqm / num_lots

    # 2. Calculate acquisition costs
    stamp_duty = calculate_stamp_duty(purchase_price)
    legals = 5000  # Conveyancing + due diligence

    # 3. Subdivision costs
    base_subdivision = (
        SUBDIVISION_COSTS["town_planner"]
        + SUBDIVISION_COSTS["surveyor"]
        + SUBDIVISION_COSTS["council_fees"]
        + SUBDIVISION_COSTS["plan_certification"]
        + SUBDIVISION_COSTS["titles_office"]
    )

    # Additional costs per new lot
    per_lot_costs = SUBDIVISION_COSTS["crossover"]  # New driveway per lot

    # Fencing estimate (boundary around new lots, ~100m total)
    fencing = SUBDIVISION_COSTS["fencing"] * 100

    subdivision_costs = base_subdivision + (per_lot_costs * (num_lots - 1)) + fencing

    # 4. Finance costs
    loan_amount = (purchase_price + subdivision_costs * 0.5) * lvr
    finance_cost = loan_amount * interest_rate * (holding_months / 12)

    # 5. Selling costs
    original_land_rate = purchase_price / land_size_sqm
    price_per_lot = estimate_lot_value(suburb, actual_lot_size, original_land_rate)
    gdv = price_per_lot * num_lots

    agent_fees = gdv * AGENT_COMMISSION
    marketing = MARKETING_PER_LOT * num_lots
    selling_costs = agent_fees + marketing

    # 6. GST (marginal scheme)
    # GST only on profit, not on original land
    gst = max(0, (gdv - purchase_price)) / 11

    # 7. Total costs
    total_costs = (
        purchase_price
        + stamp_duty
        + legals
        + subdivision_costs
        + finance_cost
        + selling_costs
        + gst
    )

    # 8. Profit
    gross_profit = (
        gdv
        - purchase_price
        - stamp_duty
        - legals
        - subdivision_costs
        - finance_cost
        - selling_costs
    )
    net_profit = gross_profit - gst
    margin_percent = (net_profit / total_costs) * 100 if total_costs > 0 else 0

    # 9. ROE calculation
    cash_required = (
        purchase_price * (1 - lvr) + stamp_duty + legals + subdivision_costs  # Deposit
    )

    total_roe = (net_profit / cash_required) * 100 if cash_required > 0 else 0
    annualized_roe = ((1 + total_roe / 100) ** (12 / holding_months) - 1) * 100

    # 10. Viability check
    is_viable = margin_percent >= 15 and net_profit > 100000

    if not is_viable:
        if margin_percent < 15:
            notes.append(f"Margin {margin_percent:.1f}% below target 15%")
        if net_profit < 100000:
            notes.append(f"Profit ${net_profit:,.0f} below target $100K")

    if num_lots >= 2:
        notes.append(
            f"Subdivision: {num_lots} × {actual_lot_size:.0f}sqm lots @ ${price_per_lot:,.0f}"
        )

    return LDRZFeasibility(
        purchase_price=purchase_price,
        land_size_sqm=land_size_sqm,
        num_lots=num_lots,
        min_lot_size=min_lot_size,
        stamp_duty=stamp_duty,
        legals=legals,
        subdivision_costs=subdivision_costs,
        finance_cost=finance_cost,
        selling_costs=selling_costs,
        total_costs=total_costs,
        price_per_lot=price_per_lot,
        gdv=gdv,
        gst=gst,
        gross_profit=gross_profit,
        net_profit=net_profit,
        margin_percent=margin_percent,
        cash_required=cash_required,
        total_roe=total_roe,
        annualized_roe=annualized_roe,
        holding_months=holding_months,
        is_viable=is_viable,
        notes=notes,
    )


def print_ldrz_feasibility(f: LDRZFeasibility) -> None:
    """Print formatted LDRZ feasibility report."""
    console.print("\n[bold blue]═══ LDRZ SUBDIVISION FEASIBILITY ═══[/bold blue]\n")

    console.print("[bold]INPUTS:[/bold]")
    console.print(f"  Purchase Price:     ${f.purchase_price:>12,.0f}")
    console.print(f"  Land Size:          {f.land_size_sqm:>12,.0f} sqm")
    console.print(f"  Minimum Lot Size:   {f.min_lot_size:>12,} sqm")
    console.print(f"  Lots Created:       {f.num_lots:>12}")
    console.print(f"  Holding Period:     {f.holding_months:>12} months")

    console.print("\n[bold]COSTS:[/bold]")
    console.print(f"  Land:               ${f.purchase_price:>12,.0f}")
    console.print(f"  Stamp Duty:         ${f.stamp_duty:>12,.0f}")
    console.print(f"  Legals:             ${f.legals:>12,.0f}")
    console.print(f"  Subdivision:        ${f.subdivision_costs:>12,.0f}")
    console.print(f"  Finance:            ${f.finance_cost:>12,.0f}")
    console.print(f"  Selling:            ${f.selling_costs:>12,.0f}")
    console.print(f"  GST:                ${f.gst:>12,.0f}")
    console.print(f"  [bold]TOTAL COST:       ${f.total_costs:>12,.0f}[/bold]")

    console.print("\n[bold]REVENUE:[/bold]")
    console.print(f"  Price per Lot:      ${f.price_per_lot:>12,.0f}")
    console.print(f"  [bold]GDV:              ${f.gdv:>12,.0f}[/bold]")

    console.print("\n[bold]PROFIT:[/bold]")
    console.print(f"  Gross Profit:       ${f.gross_profit:>12,.0f}")
    console.print(f"  [bold]Net Profit:       ${f.net_profit:>12,.0f}[/bold]")
    console.print(f"  Margin:             {f.margin_percent:>12.1f}%")

    console.print("\n[bold]RETURN ON EQUITY:[/bold]")
    console.print(f"  Cash Required:      ${f.cash_required:>12,.0f}")
    console.print(f"  Total ROE:          {f.total_roe:>12.1f}%")
    console.print(f"  [bold]Annualized ROE:   {f.annualized_roe:>12.1f}%[/bold]")

    console.print("\n" + "=" * 50)
    if f.is_viable:
        console.print("[bold green]VERDICT: VIABLE ✓[/bold green]")
    else:
        console.print("[bold yellow]VERDICT: MARGINAL ⚠️[/bold yellow]")

    if f.notes:
        console.print("\n[dim]Notes:[/dim]")
        for note in f.notes:
            console.print(f"  • {note}")


# =============================================================================
# QUICK CALCULATOR
# =============================================================================


def quick_ldrz_calc(
    purchase_price: float,
    land_size_sqm: float,
    suburb: str = "donvale",
) -> None:
    """Quick LDRZ feasibility calculation with console output.

    Args:
        purchase_price: Property purchase price
        land_size_sqm: Land size in sqm
        suburb: Suburb name
    """
    console.print(f"\n[bold]Quick LDRZ Calculation: {suburb.title()}[/bold]")
    console.print(f"Land: {land_size_sqm:,.0f} sqm @ ${purchase_price:,.0f}")

    # With sewerage
    feas_sewered = calculate_ldrz_feasibility(
        purchase_price,
        land_size_sqm,
        has_sewerage=True,
        suburb=suburb,
    )

    console.print(f"\n[green]WITH Sewerage (min 2,000sqm):[/green]")
    console.print(
        f"  Lots: {feas_sewered.num_lots} × {land_size_sqm/feas_sewered.num_lots:.0f}sqm"
    )
    console.print(f"  Profit: ${feas_sewered.net_profit:,.0f}")
    console.print(f"  ROE: {feas_sewered.annualized_roe:.1f}%")

    # Without sewerage
    feas_unsewered = calculate_ldrz_feasibility(
        purchase_price,
        land_size_sqm,
        has_sewerage=False,
        suburb=suburb,
    )

    if feas_unsewered.num_lots >= 2:
        console.print(f"\n[yellow]WITHOUT Sewerage (min 4,000sqm):[/yellow]")
        console.print(
            f"  Lots: {feas_unsewered.num_lots} × {land_size_sqm/feas_unsewered.num_lots:.0f}sqm"
        )
        console.print(f"  Profit: ${feas_unsewered.net_profit:,.0f}")
        console.print(f"  ROE: {feas_unsewered.annualized_roe:.1f}%")
    else:
        console.print(
            f"\n[red]WITHOUT Sewerage: Cannot subdivide (need 8,000+ sqm)[/red]"
        )


if __name__ == "__main__":
    # Example: 2 Milne Road, Park Orchards
    quick_ldrz_calc(
        purchase_price=1_359_000,
        land_size_sqm=4629,
        suburb="park orchards",
    )

    print()

    # Full report
    feas = calculate_ldrz_feasibility(
        purchase_price=1_800_000,
        land_size_sqm=4000,
        has_sewerage=True,
        suburb="donvale",
        holding_months=12,
    )
    print_ldrz_feasibility(feas)
