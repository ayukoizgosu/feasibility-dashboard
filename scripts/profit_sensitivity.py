def calculate_conservative_profit():
    # --- Assumptions ---
    # Scenario A: Unit 3 sells for same as Unit 2 ($1.182M) due to similar size.
    # Scenario B: Unit 3 sells for premium ($1.35M) due to rear position/privacy/4th bed.

    # Costs (Fixed)
    purchase = 1_160_000
    stamp_duty = 65_800
    construction_ex = 1_091_000
    soft_costs = 123_000
    finance = 200_000
    legal = 4500

    scenarios = [
        {"label": "Conservative (Equal to Unit 2)", "u3_price": 1_182_000},
        {"label": "Optimistic (Rear Premium)", "u3_price": 1_350_000},
    ]

    print("PROFIT SENSITIVITY ANALYSIS (Unit 3 Valuation)")
    print("-" * 60)

    for s in scenarios:
        u3 = s["u3_price"]
        sales = [1_372_000, 1_182_000, u3]  # U1, U2, U3
        total_revenue = sum(sales)

        agent_fees = total_revenue * 0.022
        selling_costs = (agent_fees / 1.1) + legal

        # GST (Margin Scheme)
        # GST = (Total Revenue - Purchase) / 11
        gst = (total_revenue - purchase) / 11

        total_costs = (
            purchase
            + stamp_duty
            + construction_ex
            + soft_costs
            + finance
            + selling_costs
            + gst
        )

        net_profit = total_revenue - total_costs
        margin = (net_profit / total_costs) * 100

        print(f"Scenario: {s['label']}")
        print(f"  Unit 3 Price:   ${u3:,.0f}")
        print(f"  Total Revenue:  ${total_revenue:,.0f}")
        print(f"  Net Profit:     ${net_profit:,.0f}")
        print(f"  Return on Cost: {margin:.1f}%")
        print("-" * 30)


if __name__ == "__main__":
    calculate_conservative_profit()
