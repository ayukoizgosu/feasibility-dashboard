import sys
import time

import requests


def test_wfs():
    print("--- DIAGNOSTIC START ---")

    # 1. Check Server Availability (GetCapabilities)
    cap_url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    cap_params = {"request": "GetCapabilities", "service": "WFS"}

    print(f"\n1. Testing Server Availability (GetCapabilities)...")
    start = time.time()
    try:
        resp = requests.get(cap_url, params=cap_params, timeout=10)
        elapsed = time.time() - start
        print(f"   [SUCCESS] Status: {resp.status_code}, Time: {elapsed:.2f}s")

        # Check for layer existence
        if "open-data-platform:plan_overlay" in resp.text:
            print(
                "   [CONFIRMED] Layer 'open-data-platform:plan_overlay' found in capabilities."
            )
        else:
            print(
                "   [WARNING] Layer 'open-data-platform:plan_overlay' NOT FOUND in capabilities text!"
            )
            # Try to find similar
            import re

            matches = re.findall(r"open-data-platform:[\w_]*overlay[\w_]*", resp.text)
            if matches:
                print(f"   Did you mean: {', '.join(set(matches))}?")

    except Exception as e:
        print(f"   [FAILED] {e}")
        return

    # 2. Check Data Query (GetFeature)
    print(f"\n2. Testing Data Query (GetFeature - 1 item)...")
    data_url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    data_params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:plan_overlay",
        "outputFormat": "application/json",
        "maxFeatures": 1,
    }

    start = time.time()
    try:
        resp = requests.get(data_url, params=data_params, timeout=15)
        elapsed = time.time() - start

        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"   [SUCCESS] Status: 200, Time: {elapsed:.2f}s")
                features = data.get("features", [])
                print(f"   Got GeoJSON with {len(features)} features.")
                if features:
                    f = features[0]
                    props = f.get("properties", {})
                    print("   [PROPERTIES SAMPLE]")
                    for k, v in props.items():
                        print(f"    - {k}: {v}")
                    print(f"   [GEOMETRY] Name: {f.get('geometry_name', 'N/A')}")
            except Exception as parse_err:
                print(
                    f"   [FAILED] JSON Parse Error: {parse_err}. Content: {resp.text[:100]}..."
                )
        else:
            print(f"   [FAILED] Status: {resp.status_code}, Time: {elapsed:.2f}s")
            print(f"   Response: {resp.text[:200]}")

    except Exception as e:
        print(f"   [FAILED] Error: {e}")


if __name__ == "__main__":
    test_wfs()
if __name__ == "__main__":
    test_wfs()
