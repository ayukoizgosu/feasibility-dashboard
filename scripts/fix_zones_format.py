import os
import shutil
from pathlib import Path

import geopandas as gpd

DATA_DIR = Path("data")
BAD_GPKG = DATA_DIR / "planning_zones.gpkg"
ZIP_FILE = DATA_DIR / "planning_zones.zip"
NEW_GPKG = DATA_DIR / "planning_zones_fixed.gpkg"


def fix_format():
    if not BAD_GPKG.exists():
        print(f"File {BAD_GPKG} not found.")
        return

    print(f"Renaming {BAD_GPKG} to {ZIP_FILE}...")
    shutil.move(BAD_GPKG, ZIP_FILE)

    print("Reading data from zip file...")
    try:
        # Read from zip (geopandas handles simple zips containing shapefiles)
        gdf = gpd.read_file(f"zip://{ZIP_FILE.absolute()}")
        print(f"Successfully read {len(gdf)} features.")

        print(f"Saving to proper GeoPackage: {BAD_GPKG}...")
        gdf.to_file(BAD_GPKG, driver="GPKG")
        print("Conversion complete!")

        # Cleanup
        os.remove(ZIP_FILE)
        print("Removed temporary zip file.")

    except Exception as e:
        print(f"Error converting data: {e}")
        # Restore name if failed
        if ZIP_FILE.exists():
            shutil.move(ZIP_FILE, BAD_GPKG)


if __name__ == "__main__":
    fix_format()
    fix_format()
