from datetime import datetime

from sqlalchemy.orm import Session

from scanner.market.models import Comparable, get_db, init_db  # noqa: F401
from scanner.market.utils import parse_sold_price


def save_comparable(db: Session, data: dict):
    """Save or update a comparable sale."""
    # Create ID if missing
    listing_id = data.get("listing_id")
    if not listing_id:
        return

    uid = f"{data.get('source', 'domain')}:{listing_id}"

    # Check existence
    existing = db.query(Comparable).filter(Comparable.id == uid).first()

    # Clean price
    price = data.get("sold_price") or parse_sold_price(data.get("price_text", ""))

    # Parse date
    s_date = data.get("sold_date")
    if isinstance(s_date, str):
        try:
            # Try ISO format first (from domain.py)
            if "T" in s_date:
                s_date = datetime.fromisoformat(s_date)
            else:
                # Try parsing common formats '20 Oct 2023'
                s_date = datetime.strptime(s_date, "%d %b %Y")
        except Exception:
            s_date = None

    if existing:
        # Update fields
        existing.sold_price = (
            price or existing.sold_price
        )  # Update if we found a better price
        existing.sold_date = s_date or existing.sold_date
        existing.agent = data.get("agent") or existing.agent
        existing.agency = data.get("agency") or existing.agency
        existing.finish_quality = data.get("finish_quality") or existing.finish_quality
        existing.building_area = data.get("building_area") or existing.building_area
        existing.year_built = data.get("year_built") or existing.year_built
        existing.days_on_market = data.get("days_on_market") or existing.days_on_market
        return

    comp = Comparable(
        id=uid,
        source=data.get("source", "domain"),
        listing_id=listing_id,
        address=data.get("address"),
        suburb=data.get("suburb"),
        property_type=data.get("property_type"),
        sold_price=price,
        sold_date=s_date,
        land_area=data.get("land_size_m2"),
        building_area=data.get("building_area"),
        finish_quality=data.get("finish_quality"),
        beds=data.get("bedrooms"),
        baths=data.get("bathrooms"),
        cars=data.get("car_spaces"),
        is_renovated=str(data.get("renovated", "")),
        features_json=str(data.get("features", [])),
        agent=data.get("agent"),
        agency=data.get("agency"),
        year_built=data.get("year_built"),
        days_on_market=data.get("days_on_market"),
        url=data.get("url"),
    )
    db.add(comp)
    db.commit()


def get_suburb_stats(db: Session, suburb: str, property_type: str = "Townhouse"):
    """Get stats for a suburb."""
    query = db.query(Comparable).filter(Comparable.suburb.ilike(suburb))

    if property_type:
        query = query.filter(Comparable.property_type.ilike(f"%{property_type}%"))

    results = query.all()

    prices = [r.sold_price for r in results if r.sold_price]
    if not prices:
        return None

    prices.sort()

    return {
        "count": len(prices),
        "median": prices[len(prices) // 2],
        "p80": prices[int(len(prices) * 0.8) if len(prices) > 1 else 0],
        "min": prices[0],
        "max": prices[-1],
    }
