from scanner.market.models import Comparable, get_db

session = next(get_db())
# Look for records where we actually got some rich data
comps = (
    session.query(Comparable)
    .filter(
        (Comparable.year_built != None)
        | (Comparable.finish_quality != "Standard")
        | (Comparable.building_area != None)
    )
    .limit(20)
    .all()
)

# If nothing interesting, just show first 10
if not comps:
    comps = session.query(Comparable).limit(10).all()

print(
    f"{'Address':<30} | {'Price':<12} | {'Qual':<10} | {'Ren':<5} | {'Year':<10} | {'Agent':<20}"
)
print("-" * 100)
for c in comps:
    print(
        f"{c.address[:30]:<30} | {str(c.sold_price):<12} | {str(c.finish_quality):<10} | {str(c.is_renovated):<5} | {str(c.year_built):<10} | {str(c.agent):<20}"
    )
