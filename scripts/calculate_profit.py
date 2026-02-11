def calculate_profit():
    # --- revenue ---
    # Unit 1: Sold $1,372,000
    # Unit 2: Sold $1,182,000
    # Unit 3: Est $1,350,000 (Conservative estimate based on U1/U2)
    sales_gross = [1_372_000, 1_182_000, 1_350_000]
    total_sales = sum(sales_gross)

    # --- Costs ---
    purchase_price = 1_160_000

    # Stamp Duty (VIC) ~5.5% + fees
    stamp_duty = 63800 + 2000  # Approx slab

    # Construction (Inc GST from User) -> convert to Ex GST for P&L usually,
    # but cashflow matters. Let's do Ex GST for profit, and handle GST net position.
    build_inc_gst = 1_200_000
    build_ex_gst = build_inc_gst / 1.1

    # Soft Costs
    planning_design = 50_000  # Permits, Architect
    subdivision = 15_000
    open_space_levy = 1_160_000 * 0.05  # 5% of site value usually

    # Selling Costs
    agent_fees = total_sales * 0.022  # 2.2% inc marketing
    legal_sales = 3 * 1500

    # Interest (Holding)
    # Bought 2021, Sold 2024/25. ~3-4 years holding?
    # Say 1.5years construction, 1 year planning/settlement.
    # Land Loan: $1.16m + costs. Construction drawn down.
    # Simple Interest Est for Project: ~ $200,000 (Conservative)
    finance_cost = 200_000

    # --- Tax (GST) ---
    # Margin Scheme on Land portion?
    # GST on Sales = 1/11th of Sale Price?
    # Usually: GST Collected = Total Sales / 11
    # Less: GST Paid on Build = Build Inc GST / 11
    # Less: GST on Land (Margin Scheme) = (Total Sales - Purchase) / 11 ??
    # Be simple: GST Net Payable = (Sales / 11) - (Build GST Credits) - (Agent GST Credits)
    # Using Margin Scheme on Land: Limit GST liability to value added.
    # GST Payable = (Total Sales - Purchase Price) / 11

    gst_margin_scheme = (total_sales - purchase_price) / 11

    # Total Costs (Ex GST where claimable)
    total_dev_cost = (
        purchase_price
        + stamp_duty
        + build_ex_gst
        + planning_design
        + subdivision
        + open_space_levy
        + finance_cost
        + (agent_fees / 1.1)  # Claim back GST
        + legal_sales
    )

    gross_profit = total_sales - total_dev_cost - gst_margin_scheme
    margin = (gross_profit / total_dev_cost) * 100

    print(f"--- FEASIBILITY REPORT: Property Dashboard ---")
    print(f"REVENUE")
    print(f"  Sales Gross:    ${total_sales:,.0f}")
    print(f"    - Unit 1: $1.372m")
    print(f"    - Unit 2: $1.182m")
    print(f"    - Unit 3: $1.350m (Est)")
    print("-" * 30)
    print(f"COSTS")
    print(f"  Purchase:       ${purchase_price:,.0f}")
    print(f"  Stamp Duty:     ${stamp_duty:,.0f}")
    print(f"  Construction:   ${build_ex_gst:,.0f} (Ex GST)")
    print(f"  Planning/Soft:  ${planning_design + subdivision + open_space_levy:,.0f}")
    print(f"  Finance (Est):  ${finance_cost:,.0f}")
    print(f"  Selling/Legal:  ${(agent_fees/1.1) + legal_sales:,.0f}")
    print(f"  GST Payable:    ${gst_margin_scheme:,.0f} (Margin Scheme)")
    print("-" * 30)
    print(f"  TOTAL COSTS:    ${total_dev_cost + gst_margin_scheme:,.0f}")
    print("-" * 30)
    print(f"PROFIT")
    print(f"  Net Profit:     ${gross_profit:,.0f}")
    print(f"  Margin on Cost: {margin:.1f}%")


if __name__ == "__main__":
    calculate_profit()
