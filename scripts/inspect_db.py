from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from scanner.market.models import Comparable

DB_PATH = "sqlite:///market_data.db"
engine = create_engine(DB_PATH)
Session = sessionmaker(bind=engine)
session = Session()

count = session.query(Comparable).count()
print(f"Total Comparables: {count}")

# Show sample
comps = session.query(Comparable).limit(5).all()
for c in comps:
    print(
        f"{c.address} | {c.suburb} | {c.property_type} | ${c.sold_price} | "
        f"Qual: {c.finish_quality} | Area: {c.building_area} | Ren: {c.is_renovated}"
    )

# Check columns
inspector = inspect(engine)
columns = [c["name"] for c in inspector.get_columns("comparables")]
print(f"Columns: {columns}")
