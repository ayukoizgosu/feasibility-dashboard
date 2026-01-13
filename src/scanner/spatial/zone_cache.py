"""Zone lookup cache to reduce WFS calls."""

from datetime import datetime, timedelta

from rich.console import Console

from scanner.db import get_session
from scanner.models import CachedZone
from scanner.spatial.gis_clients import get_zones_at_point

console = Console()

ROUND_DECIMALS = 5
DEFAULT_MAX_AGE_DAYS = 30


def _round_coord(value: float) -> float:
    return round(value, ROUND_DECIMALS)


def get_zone_at_point_cached(
    lat: float,
    lon: float,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> dict | None:
    """Return zone info using cached results when possible."""
    if lat is None or lon is None:
        return None

    lat_round = _round_coord(lat)
    lon_round = _round_coord(lon)
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    with get_session() as session:
        cached = (
            session.query(CachedZone)
            .filter(
                CachedZone.lat_round == lat_round,
                CachedZone.lon_round == lon_round,
            )
            .order_by(CachedZone.fetched_at.desc())
            .first()
        )
        if cached and cached.fetched_at and cached.fetched_at >= cutoff:
            return {
                "code": cached.zone_code,
                "lga": cached.lga,
                "properties": cached.properties,
                "cached": True,
            }

    zones = get_zones_at_point(lat, lon)
    zone = zones[0] if zones else None

    with get_session() as session:
        session.add(
            CachedZone(
                lat_round=lat_round,
                lon_round=lon_round,
                zone_code=zone.get("code") if zone else None,
                lga=zone.get("lga") if zone else None,
                properties=zone or {"status": "none"},
                fetched_at=datetime.utcnow(),
            )
        )

    if not zone:
        return None

    zone["cached"] = False
    return zone
