"""
Seed database with Balwyn High and other key school zones.
This is a placeholder until full GeoJSON import is available.
"""

from shapely.geometry import Polygon

from scanner.db import get_session, init_db
from scanner.models import CachedSchoolZone


def seed_schools():
    init_db()

    schools = []

    # 1. Balwyn High School (Approximate)
    coords_balwyn = [
        (145.05, -37.82),
        (145.09, -37.82),
        (145.09, -37.79),
        (145.05, -37.79),
        (145.05, -37.82),
    ]
    schools.append(
        {
            "name": "Balwyn High School",
            "type": "Secondary",
            "rank": 98.0,
            "desc": "Top Rated Public School",
            "poly": Polygon(coords_balwyn),
        }
    )

    # 2. Box Hill High School (Approximate)
    coords_box = [
        (145.11, -37.83),
        (145.14, -37.83),
        (145.14, -37.81),
        (145.11, -37.81),
        (145.11, -37.83),
    ]
    schools.append(
        {
            "name": "Box Hill High School",
            "type": "Secondary",
            "rank": 96.0,
            "desc": "High Performing",
            "poly": Polygon(coords_box),
        }
    )

    # 3. Glen Waverley Secondary College (Approximate)
    coords_glen = [
        (145.14, -37.89),
        (145.17, -37.89),
        (145.17, -37.87),
        (145.14, -37.87),
        (145.14, -37.89),
    ]
    schools.append(
        {
            "name": "Glen Waverley Secondary College",
            "type": "Secondary",
            "rank": 97.0,
            "desc": "Very High Demand",
            "poly": Polygon(coords_glen),
        }
    )

    # 4. Balwyn North Primary School (Approximate - same box for demo)
    schools.append(
        {
            "name": "Balwyn North Primary School",
            "type": "Primary",
            "rank": 99.0,
            "desc": "Excellent Primary",
            "poly": Polygon(coords_balwyn),
        }
    )

    with get_session() as session:
        for s in schools:
            poly = s["poly"]
            bounds = (
                poly.bounds
            )  # (minx, miny, maxx, maxy) -> (min_lon, min_lat, max_lon, max_lat)

            zone = CachedSchoolZone(
                school_name=s["name"],
                school_type=s["type"],
                year=2024,
                rank_score=s["rank"],
                rank_description=s["desc"],
                geom_wkt=poly.wkt,
                min_lon=bounds[0],
                min_lat=bounds[1],
                max_lon=bounds[2],
                max_lat=bounds[3],
                attributes={
                    "comment": "Approximate zone used for testing School Zone Analysis"
                },
            )

            # Check if exists
            exists = (
                session.query(CachedSchoolZone).filter_by(school_name=s["name"]).first()
            )
            if not exists:
                session.add(zone)
                print(f"Added {s['name']} zone.")
            else:
                print(f"Skipping {s['name']} (already exists).")

    print("School seeding complete.")


if __name__ == "__main__":
    seed_schools()
if __name__ == "__main__":
    seed_schools()
