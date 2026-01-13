"""Local cache for planning overlays (HO, BMO, PAO, EAO).

Downloads overlay polygons from Vicmap WFS to local SQLite to avoid slow API calls.
Uses in-memory spatial index (STRtree) for fast lookup.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

from rich.console import Console
from shapely import wkt
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from scanner.db import get_session
from scanner.models import CachedOverlay
from scanner.spatial.gis_clients import LAYER_PLANNING_OVERLAY, VICMAP_WFS_BASE

console = Console()

# Melbourne Metro Bounding Box (approximate)
# Covers Werribee to Pakenham, Craigieburn to Frankston
MELBOURNE_BBOX = (144.40, -38.25, 145.60, -37.40)

# Overlays to cache (Quick-kill blockers)
CACHE_OVERLAY_TYPES = ["HO", "BMO", "PAO", "EAO"]


class OverlayCacheManager:
    """Manages local caching and querying of planning overlays."""

    _instance = None
    _tree: Optional[STRtree] = None
    _overlays: list[CachedOverlay] = []
    _geometries: list[Any] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OverlayCacheManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Initialize lazily
        pass

    def ensure_loaded(self):
        """Load cache from DB into memory if not already loaded."""
        if self._tree is not None:
            return

        with get_session() as session:
            # Load all cached overlays
            self._overlays = session.query(CachedOverlay).all()

            if not self._overlays:
                # console.print("[dim]Overlay cache empty, using WFS fallback...[/dim]")
                return

            # Build geometries
            self._geometries = []
            valid_overlays = []

            for ov in self._overlays:
                try:
                    if ov.geom_wkt:
                        geom = wkt.loads(ov.geom_wkt)
                        self._geometries.append(geom)
                        valid_overlays.append(ov)
                except Exception:
                    continue

            self._overlays = valid_overlays  # Keep aligned

            if self._geometries:
                self._tree = STRtree(self._geometries)
                console.print(
                    f"[dim]Loaded {len(self._geometries)} overlays into spatial index[/dim]"
                )

    def get_overlays_at_point(self, lat: float, lon: float) -> list[dict[str, Any]]:
        """Find cached overlays intersecting a point."""
        self.ensure_loaded()

        if not self._tree:
            return []

        p = Point(lon, lat)

        # Query STRtree
        indices = self._tree.query(p, predicate="intersects")

        results = []
        for idx in indices:
            overlay = self._overlays[idx]
            results.append(
                {
                    "type": overlay.overlay_type,
                    "code": overlay.overlay_code,
                    "lga": overlay.lga,
                    "source": "cache",
                }
            )

        return results

    def populate(self, force_refresh: bool = False):
        """Download overlays from WFS and populate cache."""

        with get_session() as session:
            # Check if cache exists
            count = session.query(CachedOverlay).count()
            if count > 0 and not force_refresh:
                # Check age
                last_fetch = (
                    session.query(CachedOverlay.fetched_at)
                    .order_by(CachedOverlay.fetched_at.desc())
                    .first()
                )
                if last_fetch and last_fetch[0]:
                    age = datetime.utcnow() - last_fetch[0]
                    if age < timedelta(days=30):
                        console.print(
                            f"[green]Overlay cache valid ({count} items, {age.days} days old)[/green]"
                        )
                        return

            console.print("[blue]Refreshing overlay cache from Vicmap WFS...[/blue]")

            # Clear existing
            session.query(CachedOverlay).delete()
            session.commit()

            total_cached = 0

            # Download by type to avoid huge requests and timeouts
            # Or download all with filter

            # Use CQL Filter: OVERLAY_CODE IN ('HO', 'BMO'...) AND BBOX(...)
            # Note: WFS 2.0 uses 'filter' XML usually, but many support CQL_FILTER param
            # Vicmap supports CQL_FILTER

            # Construct CQL filter
            # Vicmap attribute: SCHEME_CODE (LGA), OVERLAY_CODE (e.g. HO)
            # Actually checking metadata: V_PLAN_OVERLAY has 'POLYZONE' (Overlay Code) or 'ZONE_CODE'
            # Let's check `gis_clients.py` results?
            # Reverting to type filter: "types" argument in query? No.
            # We'll fetch logical chunks.

            # We will query each type separately to be safe with timeouts

            # Mapping common codes:
            # HO = Heritage
            # BMO = Bushfire (WMO in old data, BMO in new)
            # PAO = Public Acquisition
            # EAO = Env Audit

            # Vicmap Planning Overlay usually has 'ZONE_CODE' (e.g., HO1, BMO)
            # Or 'SCHEME_CODE'

            # Let's try downloading query with feature limit and paging.

            # WARNING: We don't have a robust `query_wfs_paging` in gis_clients.
            # I'll implement a simple one here.

            # Use standard BBOX parameter
            # WFS 1.1.0 usually defaults to Lon/Lat (x/y) unless URN is used
            # We'll use simple Lon, Lat order which is safer for Geoserver defaults
            lon_min, lat_min, lon_max, lat_max = MELBOURNE_BBOX
            bbox_param = f"{lon_min},{lat_min},{lon_max},{lat_max},EPSG:4326"
            page_size = 1000

            # Note: geometry_name is 'geom' (confirmed by diagnostic)

            params = {
                "service": "WFS",
                "version": "1.1.0",
                "request": "GetFeature",
                "typeName": LAYER_PLANNING_OVERLAY,
                "outputFormat": "application/json",
                # "srsName": "EPSG:4326", # Optional in 1.1.0
                "bbox": bbox_param,
                "maxFeatures": str(page_size),  # maxFeatures in 1.1.0, count in 2.0.0
            }

            # Pagination loop
            start_index = 0
            while True:
                params["startIndex"] = start_index
                try:
                    resp = query_wfs_raw(params)
                    features = resp.get("features", [])
                    if not features:
                        break

                    for feat in features:
                        save_feature(session, feat)

                    total_cached += len(features)
                    console.print(
                        f"  Fetched {len(features)} overlays (total {total_cached})..."
                    )

                    if len(features) < 1000:
                        break

                    start_index += 1000
                    session.commit()

                except Exception as e:
                    console.print(f"[red]Error downloading overlays: {e}[/red]")
                    break

            session.commit()
            console.print(f"[green]Cached {total_cached} overlays[/green]")

            # Reset memory cache
            self._tree = None
            self.ensure_loaded()


def query_wfs_raw(params: dict) -> dict:
    """Helper for raw WFS request with retry."""
    # Use existing session factory
    from scanner.spatial.gis_clients import _get_session

    session = _get_session()

    # Needs to handle the namespace correctly if not in params
    # Assuming params are complete
    resp = session.get(VICMAP_WFS_BASE, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def save_feature(session, feature: dict):
    """Save a single GeoJSON feature to DB."""
    props = feature.get("properties", {})
    geom_data = feature.get("geometry")

    if not geom_data:
        return

    try:
        # Determine type
        code = props.get("ZONE_CODE") or props.get("LZONE_CODE") or ""
        otype = "OTHER"
        if code.startswith("HO"):
            otype = "HO"
        elif code.startswith("BMO") or code.startswith("WMO"):
            otype = "BMO"
        elif code.startswith("PAO"):
            otype = "PAO"
        elif code.startswith("EAO"):
            otype = "EAO"

        # Don't save if not target type (though CQL filter should handle this)
        if otype == "OTHER":
            return

        geom = shape(geom_data)
        bounds = geom.bounds

        overlay = CachedOverlay(
            feature_id=str(props.get("pfi") or props.get("PFI") or feature.get("id")),
            overlay_type=otype,
            overlay_code=code,
            lga=props.get("LGA_NAME") or props.get("LGA_CODE"),
            geom_wkt=geom.wkt,
            min_lon=bounds[0],
            min_lat=bounds[1],
            max_lon=bounds[2],
            max_lat=bounds[3],
            attributes=props,
        )
        session.merge(overlay)

    except Exception:
        pass


# Singleton instance
_manager = OverlayCacheManager()


def check_overlays_cached(lat: float, lon: float) -> list[dict[str, Any]]:
    """Check cache for overlays at point. Returns list of matches."""
    return _manager.get_overlays_at_point(lat, lon)


def has_cache_data() -> bool:
    """Check if overlay cache has data."""
    with get_session() as session:
        return session.query(CachedOverlay).count() > 0


def ensure_overlay_cache():
    """Ensure cache is populated."""
    _manager.populate()


def run():
    """Run overlay cache population manually."""
    console.print("[bold blue]Overlay Cache Manager[/bold blue]")
    ensure_overlay_cache()
    console.print("[green]✓ Overlay cache is ready[/green]")


if __name__ == "__main__":
    run()
