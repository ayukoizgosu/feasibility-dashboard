"""
Script to recreate the database and update schema.
Since we modified models (PlanningZone bbox), we need to drop/recreate tables or migrate.
For simplicity in this dev environment, we'll recreate if requested, or just ensure columns exist.

Actually, SQLite won't easily drop columns but adding is fine (if using Alembic).
Here we will just 'init_db' which creates if not exists.
Since we changed the model to add columns, existing rows won't have the columns if the table exists.
We should drop the PlanningZone table to ensure it's fresh for the bulk load.
"""

from sqlalchemy import text

from scanner.db import engine, init_db


def reset_planning_tables():
    print("Dropping PlanningZone table to apply schema changes...")
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP TABLE IF EXISTS planning_zones"))
            conn.commit()
            print("Dropped planning_zones.")
        except Exception as e:
            print(f"Error dropping table: {e}")

    print("Re-initializing database...")
    init_db()
    print("Database ready. You can now run the loader.")


if __name__ == "__main__":
    reset_planning_tables()
if __name__ == "__main__":
    reset_planning_tables()
