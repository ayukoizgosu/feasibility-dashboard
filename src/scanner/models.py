"""SQLAlchemy models for Site Scanner."""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class RawListing(Base):
    """Raw listing data from scrapers."""

    __tablename__ = "raw_listings"

    id = Column(String(64), primary_key=True)  # source:listing_id
    source = Column(String(20), nullable=False)  # 'domain' or 'rea'
    listing_id = Column(String(32), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    url = Column(Text)
    payload = Column(JSON)

    __table_args__ = (
        UniqueConstraint("source", "listing_id", name="uq_source_listing"),
    )


class Site(Base):
    """Normalized site/property record."""

    __tablename__ = "sites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Source tracking
    source = Column(String(20))  # 'domain', 'rea', or 'both'
    domain_listing_id = Column(String(32), unique=True, nullable=True)
    rea_listing_id = Column(String(32), unique=True, nullable=True)
    url = Column(Text)

    # Address
    address_raw = Column(Text)
    address_norm = Column(Text)
    street_number = Column(String(20))
    street_name = Column(String(100))
    suburb = Column(String(50))
    postcode = Column(String(10))
    state = Column(String(10), default="VIC")

    # Geocoding
    lat = Column(Float)
    lon = Column(Float)
    geocode_provider = Column(String(20))
    geocode_confidence = Column(Float)
    geocode_status = Column(
        String(20)
    )  # 'pending', 'success', 'failed', 'low_confidence'

    # Parcel info (after spatial join)
    parcel_id = Column(String(50))
    land_area_m2 = Column(Float)

    # Listing details
    property_type = Column(String(30))  # 'house', 'vacant_land'
    price_display = Column(String(100))  # As shown on listing
    price_low = Column(Float)
    price_high = Column(Float)
    price_guide = Column(Float)  # Best guess single value
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    car_spaces = Column(Integer)
    land_size_listed = Column(Float)  # As per listing

    # Status
    listing_status = Column(
        String(20), default="active"
    )  # 'active', 'under_offer', 'sold'
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Processing flags
    requires_manual_review = Column(Boolean, default=False)
    review_reason = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    constraints = relationship(
        "SiteConstraint", back_populates="site", cascade="all, delete-orphan"
    )
    feasibility_runs = relationship(
        "FeasibilityRun", back_populates="site", cascade="all, delete-orphan"
    )


class VicParcel(Base):
    """Victorian cadastre parcel."""

    __tablename__ = "vic_parcels"

    parcel_id = Column(String(50), primary_key=True)
    # Geometry stored as WKT for SQLite compatibility
    geom_wkt = Column(Text)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    area_m2 = Column(Float)
    attributes = Column(JSON)


class PlanningZone(Base):
    """Victorian planning zone."""

    __tablename__ = "planning_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_code = Column(String(20), index=True)  # e.g., 'GRZ1', 'NRZ', 'C1Z'
    lga = Column(String(50))
    geom_wkt = Column(Text)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    attributes = Column(JSON)


class PlanningOverlay(Base):
    """Victorian planning overlay."""

    __tablename__ = "planning_overlays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    overlay_code = Column(String(20), index=True)  # e.g., 'HO123', 'DDO1', 'LSIO'
    overlay_type = Column(String(10))  # Base type: 'HO', 'DDO', etc.
    lga = Column(String(50))
    geom_wkt = Column(Text)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    attributes = Column(JSON)


class SiteConstraint(Base):
    """Evaluated constraint for a site."""

    __tablename__ = "site_constraints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), index=True)

    constraint_key = Column(
        String(50)
    )  # e.g., 'zone', 'overlay:HO', 'transmission_line'
    constraint_type = Column(String(20))  # 'zone', 'overlay', 'proximity'
    code = Column(String(20))  # Zone or overlay code
    severity = Column(Integer, default=0)  # 0-3
    description = Column(Text)
    details = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="constraints")


class FeasibilityRun(Base):
    """Feasibility calculation result."""

    __tablename__ = "feasibility_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), index=True)

    # Input assumptions used
    assumptions = Column(JSON)

    # Yield estimates
    dwellings_low = Column(Integer)
    dwellings_base = Column(Integer)
    dwellings_high = Column(Integer)
    yield_confidence = Column(Float)

    # Cost estimates
    land_cost = Column(Float)
    build_cost = Column(Float)
    soft_costs = Column(Float)
    contingency = Column(Float)
    holding_costs = Column(Float)
    selling_costs = Column(Float)
    total_cost_low = Column(Float)
    total_cost_base = Column(Float)
    total_cost_high = Column(Float)

    # Revenue estimates
    sale_price_per_dwelling = Column(Float)
    revenue_low = Column(Float)
    revenue_base = Column(Float)
    revenue_high = Column(Float)

    # Profit
    profit_low = Column(Float)
    profit_base = Column(Float)
    profit_high = Column(Float)
    margin_base = Column(Float)

    # Final score (higher = better opportunity)
    score = Column(Float, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="feasibility_runs")


class GeocodingLog(Base):
    """Track geocoding usage for rate limiting."""

    __tablename__ = "geocoding_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(20))
    date = Column(String(10))  # YYYY-MM-DD
    count = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("provider", "date", name="uq_provider_date"),)


class TransmissionLine(Base):
    """Cached transmission line from Geoscience Australia WFS.

    Used to avoid repeated API calls for transmission line proximity checks.
    Lines are cached after first fetch and refreshed periodically.
    """

    __tablename__ = "transmission_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(String(50), unique=True)  # GA feature identifier
    voltage_kv = Column(Integer, index=True)  # Operating voltage: 66, 220, 500, etc.
    owner = Column(String(100))  # AusNet, Transgrid, etc.
    name = Column(String(200))  # Line name if available
    geom_wkt = Column(Text)  # LineString geometry as WKT
    min_lat = Column(Float)  # Bounding box for spatial queries
    max_lat = Column(Float)
    min_lon = Column(Float)
    max_lon = Column(Float)
    attributes = Column(JSON)  # Full properties from WFS
    fetched_at = Column(DateTime, default=datetime.utcnow)


class CachedZone(Base):
    """Cached planning zone lookup by coordinate."""

    __tablename__ = "cached_zones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lat_round = Column(Float, index=True)
    lon_round = Column(Float, index=True)
    zone_code = Column(String(20))
    lga = Column(String(50))
    properties = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class CachedOverlay(Base):
    """Cached planning overlay (Polygon)."""

    __tablename__ = "cached_overlays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(String(100), unique=True)
    overlay_type = Column(String(50))  # HO, BMO, PAO, EAO
    overlay_code = Column(String(50))  # HO123
    geom_wkt = Column(Text)  # WKT Polygon/MultiPolygon
    attributes = Column(JSON)
    bbox_min_lat = Column(Float)
    bbox_min_lon = Column(Float)
    bbox_max_lat = Column(Float)
    bbox_max_lon = Column(Float)


class CachedFengShui(Base):
    """Cached features for Feng Shui analysis."""

    __tablename__ = "cached_feng_shui"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_id = Column(String(100), unique=True)
    feature_type = Column(String(50))  # PUZ1, WATER, ROAD_NODE
    attributes = Column(JSON)
    geom_wkt = Column(Text)
    bbox_min_lat = Column(Float)
    bbox_min_lon = Column(Float)
    bbox_max_lat = Column(Float)
    bbox_max_lon = Column(Float)

    fetched_at = Column(DateTime, default=datetime.utcnow)


# Indexes for common queries

Index("ix_sites_suburb", Site.suburb)
Index("ix_sites_listing_status", Site.listing_status)
Index("ix_sites_geocode_status", Site.geocode_status)

Index("ix_cached_zones_lat_lon", CachedZone.lat_round, CachedZone.lon_round)
