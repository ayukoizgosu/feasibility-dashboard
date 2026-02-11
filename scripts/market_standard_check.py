def calculate_market_standard_cost():
    # --- Assumptions (Standard Retail Builder) ---
    # Premium Specs: Miele, Stone, Timber floors, Double Glazing.
    # July 2021 Contract Rates (Market Standard)

    RATE_DWELLING = 2850  # $/sqm - Premium Retail
    RATE_GARAGE = 1600  # $/sqm
    RATE_PORCH = 1200  # $/sqm

    # Allowances (Retail margins on site costs)
    SITE_LANDSCAPING = 300000

    # Data from User Image (Exact Areas)
    units = [
        {"label": "Unit 1", "living": 174.06, "garage": 35.75, "porch": 3.57},
        {"label": "Unit 2", "living": 142.64, "garage": 38.16, "porch": 2.68},
        {"label": "Unit 3", "living": 143.48, "garage": 38.39, "porch": 3.50},
    ]

    total_structure = 0

    for u in units:
        cost = (
            (u["living"] * RATE_DWELLING)
            + (u["garage"] * RATE_GARAGE)
            + (u["porch"] * RATE_PORCH)
        )
        total_structure += cost

    total_ex_gst = total_structure + SITE_LANDSCAPING
    total_inc_gst = total_ex_gst * 1.1

    print(f"MARKET STANDARD COSTS (July 2021 Rate Basis)")
    print(f"Structure: ${total_structure:,.0f}")
    print(f"Site/Ext:  ${SITE_LANDSCAPING:,.0f}")
    print(f"Total Ex:  ${total_ex_gst:,.0f}")
    print(f"Total Inc: ${total_inc_gst:,.0f}")

    # Profit Check
    revenue = 3736000
    land = 1160000
    costs = (
        total_ex_gst + 65800 + 200000 + 82500 + 120000
    )  # Stamp, Finance, Agents, Soft
    gst = (revenue - land) / 11

    net_profit = revenue - costs - gst
    margin = (net_profit / (costs + gst + land)) * 100  # Approx ROC

    print(f"Net Profit: ${net_profit:,.0f}")
    print(f"Margin: {margin:.1f}%")


if __name__ == "__main__":
    calculate_market_standard_cost()
