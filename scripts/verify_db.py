import sys

from scanner.market.models import Comparable, SessionLocal

try:
    db = SessionLocal()
    count = db.query(Comparable).count()
    de_count = (
        db.query(Comparable).filter(Comparable.suburb.ilike("%Doncaster East%")).count()
    )
    print(f"DEBUG: Total records: {count}")
    print(f"DEBUG: Doncaster East records: {de_count}")

    # Show last 5
    last_5 = db.query(Comparable).order_by(Comparable.id.desc()).limit(5).all()
    for c in last_5:
        print(f"  - {c.suburb}: {c.sold_price} ({c.sold_date})")

    db.close()
except Exception as e:
    print(f"ERROR: {e}")
    print(f"ERROR: {e}")
