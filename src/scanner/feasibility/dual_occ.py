"""Dual Occupancy Feasibility Engine."""

from pathlib import Path
from typing import Any

import yaml

from scanner.config import get_config
from scanner.models import Site

# Load specs
SPECS_FILE = Path("config/dual_occ_specs.yaml")
SPECS = {}
if SPECS_FILE.exists():
    with open(SPECS_FILE, encoding="utf-8") as f:
        SPECS = yaml.safe_load(f)


class DualOccFeasibility:
    def __init__(self, site: Site):
        self.site = site
        self.config = get_config()
        self.specs = SPECS.get("products", {})
        self.assumptions = SPECS.get("assumptions", {})

    def determine_best_use(self) -> str | None:
        """Decide if site suits Side-by-Side or Townhouses."""
        area = self.site.land_area_m2 or self.site.land_size_listed or 0

        # Simple heuristic for now
        # Ideally would use frontage but that requires geocoding + parcel data which we might not have yet
        # for a quick scan. If we do have it, use it.

        if area < self.assumptions.get("site_requirements", {}).get("min_area_m2", 650):
            return None

        # Default to Side-by-Side if we don't know width, as it's the target luxury product
        return "luxury_side_by_side"

    def calculate_margin(self, grv_per_unit: float) -> dict[str, Any]:
        """Calculate feasibility margin based on a target GRV."""
        product_key = self.determine_best_use()
        if not product_key:
            return {"viable": False, "reason": "Site too small"}

        product = self.specs.get(product_key)
        if not product:
            return {"viable": False, "reason": "Unknown product"}

        # 1. Revenue
        num_dwellings = 2
        total_revenue = grv_per_unit * num_dwellings

        # 2. Development Costs
        # Construction
        gfa_m2 = product["target_gfa_sq"] * 9.2903  # sq to m2
        build_cost = gfa_m2 * product["build_cost_per_m2"] * num_dwellings

        # Soft Costs
        soft = self.assumptions.get("soft_costs", {})
        consultants = soft.get("planning_permits", 30000) + soft.get(
            "architect_engineering", 40000
        )
        contributions = 0  # Open space often not applicable for 2 subdivided lots in some councils, or handled differently. keeping conservative.

        # Statutory
        subdiv_fees = soft.get("subdivision_fees", 15000)

        # Contingency
        contingency = build_cost * product.get("contingency_pct", 0.10)

        # Marketing/Sales
        sales_costs = total_revenue * product.get("sales_marketing_pct", 0.035)

        # Finance (Simplified)
        # Interest on land + build (roughly 50% drawn avg)
        # We don't know land price yet if we are calculating residual, but if we have an asking price:
        asking_price = self.site.price_guide or (
            (self.site.price_low + self.site.price_high) / 2
            if self.site.price_low
            else None
        )

        if not asking_price:
            return {"viable": False, "reason": "No price guide"}

        land_interest = (
            asking_price
            * soft.get("interest_rate_pa", 0.08)
            * (soft.get("project_duration_months", 18) / 12)
        )
        build_interest = (
            build_cost
            * 0.5
            * soft.get("interest_rate_pa", 0.08)
            * (soft.get("project_duration_months", 18) / 12)
        )
        finance_costs = land_interest + build_interest

        # Total Costs (Excluding Land)
        dev_costs_ex_land = (
            build_cost
            + consultants
            + subdiv_fees
            + contingency
            + sales_costs
            + build_interest
        )

        # 3. Residual Land Value & Margin
        # Total Cost = Land + AcqCosts + DevCostsExLand
        # AcqCosts ~ 5.5% of Land (Stamp Duty)
        stamp_duty_rate = 0.055

        total_dev_cost = (
            asking_price
            * (1 + stamp_duty_rate + (soft.get("interest_rate_pa", 0.08) * 1.5))
            + dev_costs_ex_land
        )  # Rough interest calc fix

        # Let's do a clearer margin on cost
        total_project_cost = (
            asking_price * (1 + stamp_duty_rate) + finance_costs + dev_costs_ex_land
        )

        profit = total_revenue - total_project_cost
        margin_on_cost = (profit / total_project_cost) * 100

        return {
            "viable": margin_on_cost > 15.0,  # Target 15-20%
            "margin_percent": margin_on_cost,
            "profit": profit,
            "total_revenue": total_revenue,
            "total_cost": total_project_cost,
            "product": product["name"],
            "grv_per_unit": grv_per_unit,
            # Detailed Breakdown for Report
            "target_gfa_sq": product["target_gfa_sq"],
            "build_rate_m2": product["build_cost_per_m2"],
            "est_construction_cost": build_cost,
            "site_acquisition_cost": asking_price * (1 + stamp_duty_rate),
            "finance_cost": finance_costs,
            "consultants_fees": consultants + subdiv_fees,
        }
