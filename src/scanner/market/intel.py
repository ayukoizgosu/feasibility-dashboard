"""Enhanced Market Intelligence for GRV Analysis.

This module queries the comparables database to provide data-backed
purchase price estimates with property type, quality, and age adjustments.
"""

from datetime import datetime, timedelta
from typing import Optional

from scanner.market.classifiers import (
    classify_finish_quality,
    classify_property_type,
    classify_renovation_status,
    estimate_construction_cost,
    estimate_improvement_value,
    estimate_land_value,
    get_era_depreciation_factor,
    infer_year_built,
)
from scanner.market.models import Comparable, SessionLocal


def get_comparable_sales(
    suburb: str,
    property_type: str | None = None,
    land_area_min: float | None = None,
    land_area_max: float | None = None,
    months_lookback: int = 12,
    limit: int = 50,
) -> list[Comparable]:
    """Query comparable sales from the market database.

    Args:
        suburb: Suburb name to search
        property_type: Filter by property type (House, Townhouse, etc.)
        land_area_min: Minimum land area in sqm
        land_area_max: Maximum land area in sqm
        months_lookback: How many months back to search
        limit: Max number of results

    Returns:
        List of Comparable objects
    """
    db = SessionLocal()
    try:
        query = db.query(Comparable).filter(Comparable.suburb.ilike(f"%{suburb}%"))

        # Filter by property type
        if property_type:
            query = query.filter(Comparable.property_type.ilike(f"%{property_type}%"))

        # Filter by land area range
        if land_area_min:
            query = query.filter(Comparable.land_area >= land_area_min)
        if land_area_max:
            query = query.filter(Comparable.land_area <= land_area_max)

        # Filter by date (recent sales only)
        cutoff_date = datetime.now() - timedelta(days=months_lookback * 30)
        query = query.filter(Comparable.sold_date >= cutoff_date)

        # Filter out null prices
        query = query.filter(Comparable.sold_price.isnot(None))

        # Order by most recent first
        query = query.order_by(Comparable.sold_date.desc())

        return query.limit(limit).all()
    finally:
        db.close()


def calculate_adjusted_price(
    comp: Comparable,
    subject_land_area: float,
    subject_property_type: str,
    subject_quality: str = "Standard",
) -> dict:
    """Calculate an adjusted price for a comparable sale.

    Adjusts the sold price based on:
    - Land size difference
    - Property type difference
    - Quality difference (if inferable)

    Returns dict with adjusted_price and adjustment_breakdown
    """
    adjustments = []
    multiplier = 1.0

    # 1. Land Size Adjustment (most important for development)
    if comp.land_area and comp.land_area > 0:
        land_ratio = subject_land_area / comp.land_area
        # Clamp adjustment to ±30%
        land_adjustment = max(0.7, min(1.3, land_ratio))
        if abs(land_adjustment - 1.0) > 0.02:
            adjustments.append(
                {
                    "factor": "Land Size",
                    "comp_value": f"{comp.land_area:.0f}sqm",
                    "subject_value": f"{subject_land_area:.0f}sqm",
                    "adjustment": f"{(land_adjustment - 1) * 100:+.0f}%",
                }
            )
            multiplier *= land_adjustment

    # 2. Property Type Adjustment
    comp_type = classify_property_type(comp.property_type, comp.land_area, comp.address)
    type_adjustments = {
        # (comp_type, subject_type): adjustment
        ("House", "House"): 1.0,
        ("House", "Townhouse"): 0.85,
        ("House", "Acreage"): 1.15,
        ("Townhouse", "House"): 1.15,
        ("Townhouse", "Townhouse"): 1.0,
        ("Acreage", "House"): 0.90,
        ("Acreage", "Acreage"): 1.0,
    }
    type_key = (comp_type, subject_property_type)
    type_adj = type_adjustments.get(type_key, 1.0)
    if type_adj != 1.0:
        adjustments.append(
            {
                "factor": "Property Type",
                "comp_value": comp_type,
                "subject_value": subject_property_type,
                "adjustment": f"{(type_adj - 1) * 100:+.0f}%",
            }
        )
        multiplier *= type_adj

    # 3. Quality Adjustment (if we can infer comp quality)
    comp_quality = comp.finish_quality or classify_finish_quality(
        description=None,  # We don't store full description
        sold_price=comp.sold_price,
        building_area=comp.building_area,
    )
    quality_values = {"Basic": 0, "Standard": 1, "Premium": 2, "Luxury": 3}
    comp_q_val = quality_values.get(comp_quality, 1)
    subj_q_val = quality_values.get(subject_quality, 1)
    quality_diff = subj_q_val - comp_q_val
    if quality_diff != 0:
        # Each tier difference is ~10%
        quality_adj = 1.0 + (quality_diff * 0.10)
        adjustments.append(
            {
                "factor": "Quality",
                "comp_value": comp_quality,
                "subject_value": subject_quality,
                "adjustment": f"{(quality_adj - 1) * 100:+.0f}%",
            }
        )
        multiplier *= quality_adj

    adjusted_price = comp.sold_price * multiplier

    return {
        "original_price": comp.sold_price,
        "adjusted_price": round(adjusted_price),
        "total_adjustment": f"{(multiplier - 1) * 100:+.1f}%",
        "adjustments": adjustments,
    }


def estimate_purchase_price_advanced(
    suburb: str,
    land_area_sqm: float,
    property_type: str = "House",
    assumed_quality: str = "Standard",
    months_lookback: int = 12,
) -> dict:
    """Advanced purchase price estimation with quality and type adjustments.

    This version:
    1. Finds similar properties (land size ±30%)
    2. Adjusts each comp for differences in land, type, and quality
    3. Returns adjusted median with confidence scoring

    Returns:
        Dict with estimate, confidence, breakdown, and comparable details
    """
    # Define land area tolerance (±30%)
    land_tolerance = 0.3
    land_min = land_area_sqm * (1 - land_tolerance)
    land_max = land_area_sqm * (1 + land_tolerance)

    # Try to get comps with land area filter
    comps = get_comparable_sales(
        suburb=suburb,
        property_type=property_type,
        land_area_min=land_min,
        land_area_max=land_max,
        months_lookback=months_lookback,
    )

    # If no results, try without land area filter (just suburb + type)
    search_method = "land_size_matched"
    if not comps:
        comps = get_comparable_sales(
            suburb=suburb,
            property_type=property_type,
            months_lookback=months_lookback,
        )
        search_method = "property_type_only"

    # If still no results, try just suburb (any property type)
    if not comps:
        comps = get_comparable_sales(
            suburb=suburb,
            months_lookback=months_lookback,
        )
        search_method = "suburb_only"

    if not comps:
        return {
            "estimate": None,
            "confidence": "none",
            "comps_count": 0,
            "data_source": "No comparable sales found",
            "comps": [],
            "search_method": "no_data",
        }

    # Calculate adjusted prices for each comp
    adjusted_results = []
    for c in comps:
        adj = calculate_adjusted_price(c, land_area_sqm, property_type, assumed_quality)
        adjusted_results.append(
            {
                "comp": c,
                "original_price": adj["original_price"],
                "adjusted_price": adj["adjusted_price"],
                "total_adjustment": adj["total_adjustment"],
                "adjustments": adj["adjustments"],
            }
        )

    # Calculate statistics on adjusted prices
    adjusted_prices = [r["adjusted_price"] for r in adjusted_results]
    adjusted_prices.sort()

    median_adjusted = adjusted_prices[len(adjusted_prices) // 2]

    # Also calculate raw median for comparison
    raw_prices = [c.sold_price for c in comps]
    raw_prices.sort()
    median_raw = raw_prices[len(raw_prices) // 2]

    # Determine confidence level
    confidence = "low"
    if search_method == "land_size_matched" and len(comps) >= 8:
        confidence = "high"
    elif search_method == "land_size_matched" and len(comps) >= 4:
        confidence = "medium"
    elif len(comps) >= 10:
        confidence = "medium"

    # Prepare detailed comp summary
    comp_summary = []
    for r in adjusted_results[:10]:  # Top 10
        c = r["comp"]
        comp_summary.append(
            {
                "address": c.address,
                "sold_price": c.sold_price,
                "adjusted_price": r["adjusted_price"],
                "sold_date": (
                    c.sold_date.strftime("%d %b %Y") if c.sold_date else "Unknown"
                ),
                "land_area": c.land_area,
                "building_area": c.building_area,
                "beds": c.beds,
                "property_type": c.property_type,
                "adjustment_pct": r["total_adjustment"],
            }
        )

    return {
        "estimate": median_adjusted,
        "estimate_raw": median_raw,
        "confidence": confidence,
        "comps_count": len(comps),
        "search_method": search_method,
        "subject_profile": {
            "land_area": land_area_sqm,
            "property_type": property_type,
            "assumed_quality": assumed_quality,
        },
        "data_source": f"Adjusted median of {len(comps)} sales in {suburb} (last {months_lookback}mo)",
        "comps": comp_summary,
        "price_range": {
            "min": min(adjusted_prices),
            "p25": (
                adjusted_prices[len(adjusted_prices) // 4]
                if len(adjusted_prices) >= 4
                else min(adjusted_prices)
            ),
            "median": median_adjusted,
            "p75": (
                adjusted_prices[int(len(adjusted_prices) * 0.75)]
                if len(adjusted_prices) >= 4
                else max(adjusted_prices)
            ),
            "max": max(adjusted_prices),
        },
    }


def estimate_development_land_value(
    suburb: str,
    land_area_sqm: float,
    months_lookback: int = 12,
) -> dict:
    """Estimate the LAND VALUE component specifically for development feasibility.

    This uses the residual method: analyzes sold prices, backs out improvement
    value, and calculates implied land rate $/sqm for the suburb.

    Returns:
        Dict with land_rate_psm, estimated_land_value, and supporting data
    """
    comps = get_comparable_sales(
        suburb=suburb,
        property_type="House",
        months_lookback=months_lookback,
    )

    if not comps:
        return {
            "land_rate_psm": None,
            "estimated_land_value": None,
            "method": "no_data",
            "comps_analyzed": 0,
        }

    # Calculate land value for each comp using residual method
    land_values = []
    land_rates = []

    for c in comps:
        if not c.sold_price or not c.land_area or c.land_area < 100:
            continue

        # Infer quality and age
        quality = c.finish_quality or classify_finish_quality(
            sold_price=c.sold_price, building_area=c.building_area
        )
        year_era = c.year_built or infer_year_built(None, None)
        is_reno = c.is_renovated == "Yes" if c.is_renovated else False

        # Get land value via residual
        result = estimate_land_value(
            sold_price=c.sold_price,
            building_area_sqm=c.building_area,
            finish_quality=quality,
            year_or_era=year_era,
            is_renovated=is_reno,
        )

        if result["land_value"]:
            land_values.append(result["land_value"])
            land_rates.append(result["land_value"] / c.land_area)

    if not land_rates:
        # Fallback: use 70% of sale price as land value (common rule of thumb)
        fallback_values = []
        for c in comps:
            if c.sold_price and c.land_area and c.land_area > 100:
                implied_land = c.sold_price * 0.70
                fallback_values.append(implied_land / c.land_area)

        if fallback_values:
            fallback_values.sort()
            median_rate = fallback_values[len(fallback_values) // 2]
            return {
                "land_rate_psm": round(median_rate),
                "estimated_land_value": round(median_rate * land_area_sqm),
                "method": "fallback_70pct",
                "comps_analyzed": len(fallback_values),
            }

        return {
            "land_rate_psm": None,
            "estimated_land_value": None,
            "method": "insufficient_data",
            "comps_analyzed": 0,
        }

    # Calculate median land rate
    land_rates.sort()
    median_rate = land_rates[len(land_rates) // 2]

    return {
        "land_rate_psm": round(median_rate),
        "estimated_land_value": round(median_rate * land_area_sqm),
        "land_rate_range": {
            "min": round(min(land_rates)),
            "median": round(median_rate),
            "max": round(max(land_rates)),
        },
        "method": "residual",
        "comps_analyzed": len(land_rates),
    }


def get_grv_analysis(
    suburb: str,
    land_area_sqm: float,
    proposed_building_sqm: float = 200,
    property_type: str = "House",
    target_quality: str = "Standard",
    months_lookback: int = 12,
) -> dict:
    """Complete Gross Realisation Value (GRV) analysis for development.

    Provides:
    1. End value estimate (what you could sell for)
    2. Land value estimate (what the dirt is worth)
    3. Construction cost estimate (what it costs to build)
    4. Feasibility margin calculation

    Returns:
        Comprehensive GRV analysis dict
    """
    # 1. End Value Estimate (what a new build could sell for)
    end_value_data = estimate_purchase_price_advanced(
        suburb=suburb,
        land_area_sqm=land_area_sqm,
        property_type=property_type,
        assumed_quality=target_quality,
        months_lookback=months_lookback,
    )

    # 2. Land Value Estimate
    land_data = estimate_development_land_value(
        suburb=suburb,
        land_area_sqm=land_area_sqm,
        months_lookback=months_lookback,
    )

    # 3. Construction Cost Estimate
    construction_data = estimate_construction_cost(
        building_area_sqm=proposed_building_sqm,
        finish_quality=target_quality,
        include_demolition=True,
        include_landscaping=True,
    )

    # 4. Feasibility Calculation
    end_value = end_value_data.get("estimate")
    land_value = land_data.get("estimated_land_value")
    construction_cost = construction_data.get("total")

    feasibility = None
    if end_value and land_value and construction_cost:
        total_cost = land_value + construction_cost
        profit = end_value - total_cost
        margin_pct = (profit / total_cost) * 100 if total_cost > 0 else 0

        feasibility = {
            "end_value": end_value,
            "land_cost": land_value,
            "construction_cost": construction_cost,
            "total_cost": total_cost,
            "gross_profit": profit,
            "margin_pct": round(margin_pct, 1),
            "viable": margin_pct >= 15,  # 15% is typical minimum developer margin
        }

    return {
        "end_value": end_value_data,
        "land_value": land_data,
        "construction": construction_data,
        "feasibility": feasibility,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# Keep original function for backwards compatibility
def estimate_purchase_price(
    suburb: str,
    land_area_sqm: float,
    property_type: str = "House",
    months_lookback: int = 12,
) -> dict:
    """Original purchase price estimation (simpler version).

    Maintained for backwards compatibility. For advanced analysis,
    use estimate_purchase_price_advanced() or get_grv_analysis().
    """
    result = estimate_purchase_price_advanced(
        suburb=suburb,
        land_area_sqm=land_area_sqm,
        property_type=property_type,
        assumed_quality="Standard",
        months_lookback=months_lookback,
    )

    # Flatten to match original return format
    return {
        "estimate": result["estimate"],
        "confidence": result["confidence"],
        "comps_count": result["comps_count"],
        "data_source": result["data_source"],
        "comps": result["comps"],
        "price_range": result["price_range"],
    }


def get_land_rate_psm(
    suburb: str,
    months_lookback: int = 12,
) -> Optional[float]:
    """Calculate average land rate per square meter for a suburb.

    This is useful for vacant land or when you want to value land component.

    Returns:
        Average $/sqm or None if insufficient data
    """
    result = estimate_development_land_value(
        suburb=suburb,
        land_area_sqm=600,  # Dummy value, we just want the rate
        months_lookback=months_lookback,
    )
    return result.get("land_rate_psm")


def get_dual_occ_grv_analysis(
    suburb: str,
    land_area_sqm: float,
    townhouse_sqm_each: float = 150,
    target_quality: str = "Standard",
    months_lookback: int = 12,
) -> dict:
    """GRV analysis specifically for dual-occupancy development.

    Calculates end value for 2x townhouses instead of a single dwelling.
    Uses townhouse comparables for more accurate end value estimation.

    Args:
        suburb: Target suburb
        land_area_sqm: Total land area
        townhouse_sqm_each: Building size per townhouse (default 150sqm)
        target_quality: Build quality tier
        months_lookback: Months of sales data to consider

    Returns:
        Comprehensive dual-occ feasibility analysis
    """
    num_dwellings = 2
    total_building_sqm = townhouse_sqm_each * num_dwellings

    # 1. Get townhouse end values (per unit)
    townhouse_ev = estimate_purchase_price_advanced(
        suburb=suburb,
        land_area_sqm=land_area_sqm / num_dwellings,  # Each has half the land
        property_type="Townhouse",
        assumed_quality=target_quality,
        months_lookback=months_lookback,
    )

    # 2. If no townhouse data, fall back to house data with adjustment
    if townhouse_ev["estimate"] is None or townhouse_ev["comps_count"] < 3:
        house_ev = estimate_purchase_price_advanced(
            suburb=suburb,
            land_area_sqm=land_area_sqm,
            property_type="House",
            assumed_quality=target_quality,
            months_lookback=months_lookback,
        )
        # Townhouses typically sell for 70-80% of equivalent house value
        if house_ev["estimate"]:
            townhouse_unit_value = int(house_ev["estimate"] * 0.75)
            townhouse_ev["estimate"] = townhouse_unit_value
            townhouse_ev["data_source"] = f"Derived from house data (75% adjustment)"
            townhouse_ev["confidence"] = "low"

    unit_end_value = townhouse_ev.get("estimate", 0) or 0
    total_end_value = unit_end_value * num_dwellings

    # 3. Land value (full site)
    land_data = estimate_development_land_value(
        suburb=suburb,
        land_area_sqm=land_area_sqm,
        months_lookback=months_lookback,
    )

    # 4. Construction cost (for both units)
    construction_per_unit = estimate_construction_cost(
        building_area_sqm=townhouse_sqm_each,
        finish_quality=target_quality,
        include_demolition=False,  # Only one demo
        include_landscaping=False,  # Shared
    )

    # Add shared costs once
    demolition = 35000
    landscaping = 50000 if target_quality in ["Standard", "Premium"] else 30000
    site_costs = 25000  # Shared costs (connections, crossovers, etc.)

    total_construction = (
        construction_per_unit["construction"] * num_dwellings
        + demolition
        + landscaping
        + site_costs
        + construction_per_unit["professional_fees"] * num_dwellings
        + construction_per_unit["contingency"] * num_dwellings
    )

    # 5. Feasibility
    land_value = land_data.get("estimated_land_value") or 0

    feasibility = None
    if total_end_value > 0 and land_value > 0:
        total_cost = land_value + total_construction
        profit = total_end_value - total_cost
        margin_pct = (profit / total_cost) * 100 if total_cost > 0 else 0

        feasibility = {
            "num_dwellings": num_dwellings,
            "unit_end_value": unit_end_value,
            "total_end_value": total_end_value,
            "land_cost": land_value,
            "construction_cost": round(total_construction),
            "total_cost": round(total_cost),
            "gross_profit": round(profit),
            "margin_pct": round(margin_pct, 1),
            "profit_per_unit": round(profit / num_dwellings),
            "viable": margin_pct
            >= 18,  # Dual-occ needs higher margin due to complexity
        }

    return {
        "strategy": "Dual-Occupancy",
        "end_value_per_unit": townhouse_ev,
        "land_value": land_data,
        "construction": {
            "per_unit": construction_per_unit,
            "demolition": demolition,
            "landscaping": landscaping,
            "site_costs": site_costs,
            "total": round(total_construction),
        },
        "feasibility": feasibility,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
