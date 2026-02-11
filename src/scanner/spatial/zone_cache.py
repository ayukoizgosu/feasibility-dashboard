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
        # 1. Check Point Cache
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

        # 2. Check Whole-of-Melbourne Polygon Cache (PlanningZone table)
        # Using BBOX subset filtering + Shapely precise check
        try:
            from shapely import Point, wkt

            from scanner.models import PlanningZone

            candidates = (
                session.query(PlanningZone)
                .filter(
                    PlanningZone.min_lat <= lat,
                    PlanningZone.max_lat >= lat,
                    PlanningZone.min_lon <= lon,
                    PlanningZone.max_lon >= lon,
                )
                .all()
            )

            p = Point(lon, lat)
            for cand in candidates:
                try:
                    poly = wkt.loads(cand.geom_wkt)
                    if poly.contains(p):
                        # Found in local cache!
                        # Populate point cache for future fast lookup
                        c_zone = CachedZone(
                            lat_round=lat_round,
                            lon_round=lon_round,
                            zone_code=cand.zone_code,
                            lga=cand.lga,
                            properties=cand.attributes,
                            fetched_at=datetime.utcnow(),
                        )
                        session.add(c_zone)
                        session.commit()

                        return {
                            "code": cand.zone_code,
                            "lga": cand.lga,
                            "properties": cand.attributes,
                            "cached": True,  # Technically cached now
                            "source": "local_polygon",
                        }
                except Exception:
                    continue
        except Exception as e:
            # Fallback to WFS if DB error or missing table
            console.print(f"[yellow]Local zone lookup failed: {e}[/yellow]")

    # 3. Fallback to WFS
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
    return zone
