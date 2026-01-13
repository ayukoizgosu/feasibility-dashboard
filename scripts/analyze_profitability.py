"""Quick profitability analysis for Donvale listings."""

from scanner.config import get_config
from scanner.db import get_session
from scanner.models import Site


def analyze_profitability():
    """Analyze subdivision potential and profitability for all sites."""

    config = get_config()

    # Feasibility assumptions from config
    build_cost_per_m2 = config.feasibility.build_cost_per_m2  # $2800
    soft_costs_pct = config.feasibility.soft_cost_pct  # 15%
    finance_rate = config.feasibility.finance_rate  # 7.5%
    holding_months = config.feasibility.holding_months  # 18

    print("=" * 70)
    print("DONVALE SUBDIVISION POTENTIAL ANALYSIS")
    print("=" * 70)
    print()
    print(
        f"Assumptions: Build ${build_cost_per_m2}/m², {soft_costs_pct*100:.0f}% soft costs, {finance_rate*100:.1f}% finance, {holding_months} months"
    )
    print()

    with get_session() as session:
        sites = session.query(Site).order_by(Site.land_size_listed.desc()).all()

        high_potential = []
        medium_potential = []
        low_potential = []

        for site in sites:
            land = site.land_size_listed or 0
            price = site.price_guide or 0

            if land == 0:
                continue

            # Estimate lots (assume min 300m2 per lot, with 20% for roads/access)
            usable_land = land * 0.8
            potential_lots = max(1, int(usable_land / 300))

            # Price per m2
            price_per_m2 = price / land if land > 0 else 0

            # Estimated townhouse sizes: 180m2 each
            townhouse_size = 180
            total_build_area = potential_lots * townhouse_size

            # Total development cost
            land_cost = price
            construction = total_build_area * build_cost_per_m2
            soft_costs = (land_cost + construction) * soft_costs_pct
            finance_cost = (
                (land_cost + construction) * finance_rate * (holding_months / 12)
            )
            total_cost = land_cost + construction + soft_costs + finance_cost

            # Estimated sale value (Donvale townhouse ~$1.1m each)
            sale_price_per_unit = 1_100_000
            total_revenue = potential_lots * sale_price_per_unit

            # Profit
            profit = total_revenue - total_cost
            profit_margin = (profit / total_cost) * 100 if total_cost > 0 else 0

            result = {
                "address": site.address_raw,
                "land_m2": land,
                "price": price,
                "price_per_m2": price_per_m2,
                "potential_lots": potential_lots,
                "total_cost": total_cost,
                "total_revenue": total_revenue,
                "profit": profit,
                "profit_margin": profit_margin,
            }

            # Classify
            if profit_margin > 20 and land > 2000:
                high_potential.append(result)
            elif profit_margin > 10 or land > 1500:
                medium_potential.append(result)
            else:
                low_potential.append(result)

        # Print results
        print("🟢 HIGH POTENTIAL (>20% margin, >2000m²)")
        print("-" * 70)
        for r in high_potential:
            print(f"  {r['address']}")
            print(
                f"    Land: {r['land_m2']:,.0f}m² @ ${r['price']:,.0f} (${r['price_per_m2']:.0f}/m²)"
            )
            print(
                f"    Potential: {r['potential_lots']} lots → ${r['total_revenue']:,.0f} revenue"
            )
            print(
                f"    Cost: ${r['total_cost']:,.0f} | Profit: ${r['profit']:,.0f} ({r['profit_margin']:.1f}%)"
            )
            print()

        print()
        print("🟡 MEDIUM POTENTIAL")
        print("-" * 70)
        for r in medium_potential[:5]:  # Top 5 only
            print(f"  {r['address']}")
            print(
                f"    Land: {r['land_m2']:,.0f}m² | {r['potential_lots']} lots | Margin: {r['profit_margin']:.1f}%"
            )
            print()

        print()
        print(
            f"🔴 LOW POTENTIAL: {len(low_potential)} sites (too small or too expensive)"
        )
        print()

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Total sites: {len(sites)}")
        print(f"  High potential: {len(high_potential)}")
        print(f"  Medium potential: {len(medium_potential)}")
        print(f"  Low potential: {len(low_potential)}")

        if high_potential:
            best = high_potential[0]
            print()
            print(f"  🏆 BEST OPPORTUNITY: {best['address']}")
            print(f"     {best['land_m2']:,.0f}m² for ${best['price']:,.0f}")
            print(
                f"     Est. profit: ${best['profit']:,.0f} ({best['profit_margin']:.1f}% margin)"
            )


if __name__ == "__main__":
    analyze_profitability()
    analyze_profitability()
