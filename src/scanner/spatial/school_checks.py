"""
School zone analysis module.
"""

import logging
from typing import Dict, List

from shapely import wkt
from shapely.geometry import Point
from sqlalchemy.orm import Session

from scanner.models import CachedSchoolZone, Site, SiteConstraint

logger = logging.getLogger(__name__)


def check_school_zones(lat: float, lon: float, session: Session) -> List[Dict]:
    """
    Check if the point falls within any cached school zones.

    Args:
        lat: Latitude
        lon: Longitude
        session: Database session.

    Returns:
        List of dictionaries containing school details.
    """
    if not lat or not lon:
        return []

    # 1. Broad phase: query by bbox
    candidates = (
        session.query(CachedSchoolZone)
        .filter(
            CachedSchoolZone.min_lat <= lat,
            CachedSchoolZone.max_lat >= lat,
            CachedSchoolZone.min_lon <= lon,
            CachedSchoolZone.max_lon >= lon,
        )
        .all()
    )

    results = []
    point = Point(lon, lat)

    for zone in candidates:
        try:
            poly = wkt.loads(zone.geom_wkt)
            if poly.contains(point):
                # Match found
                results.append(
                    {
                        "school_name": zone.school_name,
                        "school_type": zone.school_type,
                        "rank_score": zone.rank_score,
                        "rank_description": zone.rank_description,
                        "year": zone.year,
                    }
                )
                logger.info(f"Site matches school zone: {zone.school_name}")

        except Exception as e:
            logger.error(f"Error checking school zone {zone.school_name}: {e}")

    return results


def create_school_zone_constraints(
    site: Site, session: Session
) -> List[SiteConstraint]:
    """
    Helper to create SiteConstraint objects from check results.
    """
    matches = check_school_zones(site.lat, site.lon, session)
    constraints = []

    for m in matches:
        description = f"Inside zone for {m['school_name']} ({m['school_type']})"
        if m["rank_description"]:
            description += f" - {m['rank_description']}"
        elif m["rank_score"]:
            description += f" (Rank: {m['rank_score']})"

        c = SiteConstraint(
            site_id=site.id,
            constraint_key=f"school_zone:{m['school_name']}",
            constraint_type="school_zone",
            code=m["school_type"],
            severity=0,
            description=description,
            details=m,
        )
        constraints.append(c)

    return constraints
