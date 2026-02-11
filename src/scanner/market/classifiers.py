"""Property classification utilities for GRV analysis.

This module provides functions to classify properties based on
listing data, keywords, and heuristics.
"""

import re
from typing import Optional

# ============================================================================
# PROPERTY TYPE CLASSIFICATION
# ============================================================================


def classify_property_type(
    listed_type: str | None,
    land_area: float | None,
    address: str | None = None,
) -> str:
    """Classify property into standardized types.

    Returns one of:
    - "House" (standard residential block)
    - "Townhouse" (attached/strata)
    - "Acreage" (rural/semi-rural large block)
    - "Unit" (apartment/flat)
    - "Vacant Land"
    - "Unknown"
    """
    if listed_type:
        lt = listed_type.lower()

        # Direct mappings
        if any(x in lt for x in ["townhouse", "town house", "terrace"]):
            return "Townhouse"
        if any(x in lt for x in ["unit", "apartment", "flat"]):
            return "Unit"
        if any(x in lt for x in ["vacant", "land"]):
            return "Vacant Land"
        if any(x in lt for x in ["acreage", "rural", "lifestyle", "farm"]):
            return "Acreage"

    # Check address for strata indicators
    if address:
        addr_lower = address.lower()
        if re.match(r"^(unit|apt|apartment|lot)\s*\d+", addr_lower):
            return "Unit"
        if "/" in address and re.match(r"^\d+/\d+", address):
            return "Townhouse"  # Often strata

    # Land size heuristics for houses
    if land_area:
        if land_area > 2000:
            return "Acreage"
        if land_area < 150:
            return "Unit"  # Likely strata

    # Default to house if we have a listed type that mentions house
    if listed_type and "house" in listed_type.lower():
        return "House"

    return "House" if land_area and land_area > 200 else "Unknown"


# ============================================================================
# FINISH QUALITY CLASSIFICATION
# ============================================================================

# Keywords grouped by quality tier
QUALITY_KEYWORDS = {
    "Luxury": [
        "luxury",
        "luxurious",
        "prestige",
        "prestigious",
        "architect-designed",
        "bespoke",
        "premium",
        "high-end",
        "world-class",
        "state-of-the-art",
        "opulent",
        "grand",
        "masterpiece",
        "exceptional",
        "resort-style",
        "marble",
        "imported",
        "custom-built",
        "trophy home",
        "designer",
    ],
    "Premium": [
        "executive",
        "quality",
        "beautiful",
        "stunning",
        "sophisticated",
        "elegant",
        "immaculate",
        "pristine",
        "meticulously",
        "exquisite",
        "refined",
        "substantial",
        "impressive",
        "generous",
        "entertainer",
    ],
    "Standard": [
        "comfortable",
        "well-maintained",
        "neat",
        "tidy",
        "practical",
        "functional",
        "convenient",
        "family",
        "solid",
        "established",
    ],
    "Basic": [
        "original",
        "unrenovated",
        "renovator",
        "handyman",
        "potential",
        "deceased estate",
        "as-is",
        "requires work",
        "project",
        "opportunity",
        "investor",
        "dated",
        "retro",
        "needs updating",
        "blank canvas",
    ],
}

# Price per sqm benchmarks (building area) for quality inference
QUALITY_PRICE_PSM_THRESHOLDS = {
    "Luxury": 8000,  # >$8,000/sqm building
    "Premium": 5500,  # >$5,500/sqm
    "Standard": 3500,  # >$3,500/sqm
    "Basic": 0,  # Below standard
}


def classify_finish_quality(
    description: str | None = None,
    sold_price: float | None = None,
    building_area: float | None = None,
) -> str:
    """Classify finish quality based on description keywords and price metrics.

    Returns: "Luxury", "Premium", "Standard", or "Basic"
    """
    keyword_score = {"Luxury": 0, "Premium": 0, "Standard": 0, "Basic": 0}

    # Keyword analysis
    if description:
        desc_lower = description.lower()
        for quality, keywords in QUALITY_KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    keyword_score[quality] += 1

    # Price per sqm analysis (if we have building area)
    price_quality = None
    if sold_price and building_area and building_area > 50:
        price_psm = sold_price / building_area
        if price_psm >= QUALITY_PRICE_PSM_THRESHOLDS["Luxury"]:
            price_quality = "Luxury"
        elif price_psm >= QUALITY_PRICE_PSM_THRESHOLDS["Premium"]:
            price_quality = "Premium"
        elif price_psm >= QUALITY_PRICE_PSM_THRESHOLDS["Standard"]:
            price_quality = "Standard"
        else:
            price_quality = "Basic"

    # Determine winner
    # If we have strong keyword signals, use those
    max_keyword_tier = max(keyword_score, key=keyword_score.get)
    max_keyword_count = keyword_score[max_keyword_tier]

    if max_keyword_count >= 3:
        return max_keyword_tier
    elif max_keyword_count >= 1 and price_quality:
        # Blend: trust keywords if close to price indication
        tier_order = ["Basic", "Standard", "Premium", "Luxury"]
        kw_idx = tier_order.index(max_keyword_tier)
        price_idx = tier_order.index(price_quality)
        # Average the indices
        avg_idx = round((kw_idx + price_idx) / 2)
        return tier_order[avg_idx]
    elif price_quality:
        return price_quality
    elif max_keyword_count >= 1:
        return max_keyword_tier

    return "Standard"  # Default assumption


# ============================================================================
# YEAR BUILT / ERA CLASSIFICATION
# ============================================================================

ERA_KEYWORDS = {
    "Pre-1920": [
        "victorian",
        "edwardian",
        "federation",
        "heritage",
        "period",
        "historic",
    ],
    "1920-1950": [
        "inter-war",
        "interwar",
        "californian bungalow",
        "art deco",
        "1930s",
        "1940s",
    ],
    "1950-1970": [
        "mid-century",
        "1950s",
        "1960s",
        "post-war",
        "brick veneer",
        "classic",
    ],
    "1970-1990": ["1970s", "1980s", "cream brick", "split level", "contemporary"],
    "1990-2010": ["1990s", "2000s", "modern", "recently built"],
    "Post-2010": [
        "brand new",
        "near new",
        "newly built",
        "2010s",
        "2020s",
        "custom built",
    ],
}


def infer_year_built(
    listed_year: str | None = None,
    description: str | None = None,
) -> Optional[str]:
    """Infer the build era from listing data.

    Returns: Era string like "1970-1990" or actual year if known.
    """
    # If we have an explicit year, use it
    if listed_year:
        try:
            year = int(re.search(r"\d{4}", str(listed_year)).group())
            return str(year)
        except (AttributeError, ValueError):
            pass

    # Keyword-based era inference
    if description:
        desc_lower = description.lower()
        for era, keywords in ERA_KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    return era

    return None


def get_era_depreciation_factor(year_or_era: str | None) -> float:
    """Get depreciation factor for building improvements based on age.

    Returns a multiplier (0.0 to 1.0) to apply to improvement value.
    Newer buildings retain more value.
    """
    if not year_or_era:
        return 0.6  # Assume middle-aged if unknown

    # Try to extract a year
    try:
        year = int(re.search(r"\d{4}", str(year_or_era)).group())
        age = 2026 - year

        if age <= 5:
            return 1.0
        elif age <= 15:
            return 0.9
        elif age <= 30:
            return 0.7
        elif age <= 50:
            return 0.5
        else:
            return 0.3
    except (AttributeError, ValueError):
        pass

    # Era-based factors
    era_factors = {
        "Post-2010": 0.95,
        "1990-2010": 0.75,
        "1970-1990": 0.55,
        "1950-1970": 0.40,
        "1920-1950": 0.30,
        "Pre-1920": 0.25,  # Heritage value may offset
    }

    return era_factors.get(year_or_era, 0.5)


# ============================================================================
# RENOVATION STATUS
# ============================================================================

RENOVATED_KEYWORDS = [
    "renovated",
    "updated",
    "refurbished",
    "restored",
    "extended",
    "modern extension",
    "new kitchen",
    "new bathroom",
    "recently upgraded",
    "transformed",
]

UNRENOVATED_KEYWORDS = [
    "original",
    "unrenovated",
    "original condition",
    "as-is",
    "untouched",
    "retains",
    "period features intact",
    "genuine original",
]


def classify_renovation_status(description: str | None) -> str:
    """Classify renovation status.

    Returns: "Renovated", "Unrenovated", or "Unknown"
    """
    if not description:
        return "Unknown"

    desc_lower = description.lower()

    renovated_matches = sum(1 for kw in RENOVATED_KEYWORDS if kw in desc_lower)
    unrenovated_matches = sum(1 for kw in UNRENOVATED_KEYWORDS if kw in desc_lower)

    if renovated_matches > unrenovated_matches:
        return "Renovated"
    elif unrenovated_matches > renovated_matches:
        return "Unrenovated"

    return "Unknown"


# ============================================================================
# CONSTRUCTION COST ESTIMATION
# ============================================================================

# Melbourne metro construction costs ($/sqm of building area)
CONSTRUCTION_COST_PSM = {
    "Luxury": 5500,  # High-end finishes, architect-designed
    "Premium": 3800,  # Quality project home with upgrades
    "Standard": 2800,  # Standard project home
    "Basic": 2000,  # Budget build / knockdown rebuild
}


def estimate_construction_cost(
    building_area_sqm: float,
    finish_quality: str = "Standard",
    include_demolition: bool = False,
    include_landscaping: bool = True,
) -> dict:
    """Estimate construction cost for a new build.

    Args:
        building_area_sqm: Internal floor area of proposed dwelling
        finish_quality: "Luxury", "Premium", "Standard", or "Basic"
        include_demolition: Add demolition allowance (~$30k)
        include_landscaping: Add landscaping allowance (~$40k standard)

    Returns:
        Dict with cost breakdown
    """
    base_rate = CONSTRUCTION_COST_PSM.get(finish_quality, 2800)

    # Base construction cost
    construction = building_area_sqm * base_rate

    # Additional allowances
    demolition = 35000 if include_demolition else 0

    landscaping_rates = {
        "Luxury": 80000,
        "Premium": 50000,
        "Standard": 35000,
        "Basic": 20000,
    }
    landscaping = (
        landscaping_rates.get(finish_quality, 35000) if include_landscaping else 0
    )

    # Professional fees (~8-12% of construction)
    fees_pct = 0.10
    professional_fees = construction * fees_pct

    # Contingency (~5-10%)
    contingency_pct = 0.08
    contingency = (construction + professional_fees) * contingency_pct

    total = construction + demolition + landscaping + professional_fees + contingency

    return {
        "construction": round(construction),
        "demolition": round(demolition),
        "landscaping": round(landscaping),
        "professional_fees": round(professional_fees),
        "contingency": round(contingency),
        "total": round(total),
        "rate_psm": base_rate,
        "quality_tier": finish_quality,
    }


# ============================================================================
# IMPROVEMENT VALUE ESTIMATION (for existing properties)
# ============================================================================


def estimate_improvement_value(
    building_area_sqm: float | None,
    finish_quality: str = "Standard",
    year_or_era: str | None = None,
    is_renovated: bool = False,
) -> float | None:
    """Estimate the current value of existing improvements.

    This uses construction cost as a baseline, then applies:
    - Depreciation based on age
    - Renovation premium if applicable

    Returns:
        Estimated improvement value in dollars, or None if insufficient data
    """
    if not building_area_sqm or building_area_sqm < 50:
        return None

    # Base replacement cost
    base_rate = CONSTRUCTION_COST_PSM.get(finish_quality, 2800)
    replacement_cost = building_area_sqm * base_rate

    # Apply depreciation
    depreciation_factor = get_era_depreciation_factor(year_or_era)
    depreciated_value = replacement_cost * depreciation_factor

    # Renovation premium (adds back some value)
    if is_renovated:
        # Renovated properties typically add 15-25% to depreciated value
        depreciated_value *= 1.20

    return round(depreciated_value)


def estimate_land_value(
    sold_price: float,
    building_area_sqm: float | None,
    finish_quality: str = "Standard",
    year_or_era: str | None = None,
    is_renovated: bool = False,
) -> dict:
    """Estimate land value by subtracting estimated improvement value.

    This is a RESIDUAL method: Land = Sale Price - Improvements

    Returns:
        Dict with land_value, improvement_value, and land_rate_psm
    """
    improvement_value = estimate_improvement_value(
        building_area_sqm, finish_quality, year_or_era, is_renovated
    )

    if improvement_value is None:
        return {
            "land_value": None,
            "improvement_value": None,
            "land_rate_psm": None,
            "method": "insufficient_data",
        }

    # Ensure land value is at least 30% of sale price (sanity check)
    min_land_value = sold_price * 0.30
    raw_land_value = sold_price - improvement_value
    land_value = max(raw_land_value, min_land_value)

    # If we had to use minimum, adjust improvement value down
    if raw_land_value < min_land_value:
        improvement_value = sold_price - land_value

    return {
        "land_value": round(land_value),
        "improvement_value": round(improvement_value),
        "land_pct_of_sale": round(land_value / sold_price * 100, 1),
        "method": "residual",
    }
