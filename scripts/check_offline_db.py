from sqlalchemy import text

from scanner.db import get_session
from scanner.models import CachedSchoolZone, CachedZone, PlanningZone, Site


def check_db_state():
    with get_session() as session:
        # Check Address
        print("--- Address Check ---")
        sites = session.query(Site).filter(Site.address_raw.ilike("%Dryden%")).all()
        if sites:
            for s in sites:
                print(f"Found Site: {s.address_raw} ({s.lat}, {s.lon})")
        else:
            print("Address '24 Dryden St' NOT found in sites DB.")

        # Check Zoning Data
        print("\n--- Zoning Data Check ---")
        z_count = session.query(PlanningZone).count()
        print(f"PlanningZone rows: {z_count}")

        # Check School Data
        print("\n--- School Data Check ---")
        s_count = session.query(CachedSchoolZone).count()
        print(f"CachedSchoolZone rows: {s_count}")
        for s in session.query(CachedSchoolZone).all():
            print(f" - {s.school_name} ({s.school_type})")


if __name__ == "__main__":
    check_db_state()
if __name__ == "__main__":
    check_db_state()
