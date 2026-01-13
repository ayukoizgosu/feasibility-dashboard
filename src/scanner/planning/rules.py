"""Planning rules logic."""

from scanner.config import ZoneParams, get_config


def get_zone_rules(zone_code: str) -> ZoneParams:
    """Get parameters for a specific zone code."""
    config = get_config()
    return config.get_zone_params(zone_code)


def calculate_max_footprint(
    land_area: float, zone_code: str
) -> tuple[float, list[str]]:
    """
    Calculate maximum building footprint based on zone rules.
    Returns (max_footprint_sqm, reasons).
    """
    rules = get_zone_rules(zone_code)
    constraints = []

    # constraint 1: Site Coverage
    max_coverage = land_area * rules.site_coverage_max
    constraints.append(
        f"Coverage ({rules.site_coverage_max*100}%): {max_coverage:.0f}m2"
    )

    # constraint 2: Garden Area (if applicable)
    max_garden_allowed = land_area
    if rules.garden_area_min:
        # Building area can be at most (1 - garden_area)
        # Note: This is simplified. Garden area definition prevents roofed areas.
        max_garden_allowed = land_area * (1.0 - rules.garden_area_min)
        constraints.append(
            f"Garden Limit ({rules.garden_area_min*100}% min): {max_garden_allowed:.0f}m2"
        )

    return min(max_coverage, max_garden_allowed), constraints


def check_yield_limits(zone_code: str) -> int | None:
    """Return max dwellings if capped (e.g. NRZ)."""
    rules = get_zone_rules(zone_code)
    return rules.max_dwellings
