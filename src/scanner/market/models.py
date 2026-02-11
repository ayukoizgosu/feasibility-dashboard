from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Comparable(Base):
    __tablename__ = "comparables"

    id = Column(String, primary_key=True)  # domain:12345
    source = Column(String, default="domain")
    listing_id = Column(String, nullable=False)
    address = Column(String)
    suburb = Column(String)
    postcode = Column(String)
    property_type = Column(String)  # House, Townhouse, etc.

    sold_price = Column(Float)
    sold_date = Column(DateTime)

    land_area = Column(Float)
    building_area = Column(Float)  # Internal size in m2
    finish_quality = Column(String)  # Derived from keywords (Luxury, Standard, etc)

    beds = Column(Integer)
    baths = Column(Integer)
    cars = Column(Integer)

    is_renovated = Column(String)  # Yes/No or Boolean
    features_json = Column(String)  # JSON list of features
    year_built = Column(String)  # e.g. 1970s

    days_on_market = Column(Integer)
    agent = Column(String)
    agency = Column(String)

    url = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# DB Setup
DB_PATH = "sqlite:///market_data.db"
engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
