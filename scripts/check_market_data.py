"""Quick guide to populate market data and use intelligence features.

This shows:
1. How to check if you have market data
2. How to populate it (scraper commands)
3. How the purchase estimation works
"""

# Step 1: Check current market data
from scanner.market.models import Comparable, SessionLocal

db = SessionLocal()
count = db.query(Comparable).count()
print(f"\n📊 Current Market Data: {count} comparables in database")

if count > 0:
    # Show sample
    sample = db.query(Comparable).limit(5).all()
    print("\nSample records:")
    for comp in sample:
        print(
            f"  - {comp.suburb}: ${comp.sold_price:,.0f} ({comp.sold_date.strftime('%b %Y') if comp.sold_date else 'N/A'})"
        )

# Step 2: Test the intelligence
if count > 0:
    from scanner.market.intel import estimate_purchase_price

    suburbs_to_test = ["Doncaster East", "Park Orchards", "Donvale"]

    for suburb in suburbs_to_test:
        result = estimate_purchase_price(
            suburb, land_area_sqm=700, property_type="House"
        )
        if result["estimate"]:
            print(
                f"\n✅ {suburb}: ${result['estimate']:,.0f} (Confidence: {result['confidence']}, {result['comps_count']} comps)"
            )
        else:
            print(f"\n❌ {suburb}: No data")

db.close()

print("\n" + "=" * 60)
print("📝 TO POPULATE MARKET DATA:")
print("=" * 60)
print(
    """
1. For Domain scraping:
   python -m scanner.ingest.domain --suburb "Doncaster East" --limit 50

2. For REA scraping:
   python -m scanner.ingest.rea --suburb "Doncaster East" --limit 50

3. Check the data:
   python scripts/inspect_rich_db.py

4. Once populated, scan_single will automatically use this data!
"""
)
