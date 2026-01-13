import logging
import os
import sys
import traceback

# Force import from src
print(f"Original sys.path: {sys.path[:3]}")
src_path = os.path.join(os.getcwd(), "src")
sys.path.insert(0, src_path)
print(f"Modified sys.path: {sys.path[:3]}")

# Setup logging
logging.basicConfig(level=logging.DEBUG)

try:
    from scanner.spatial.gis_clients import console, get_zones_at_point
except ImportError:
    print("Could not import gis_clients even with src path!")
    sys.exit(1)


def test_zone_check():
    # 2 Quamby Place, Donvale
    lat = -37.7849813
    lon = 145.1825641

    print(f"Testing Zone Check for Lat: {lat}, Lon: {lon}")

    try:
        zones = get_zones_at_point(lat, lon)
        print(f"Zones found: {len(zones)}")
        for z in zones:
            print(f" - {z}")
            if "LDRZ" in str(z):
                print("SUCCESS: LDRZ Found!")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    test_zone_check()
