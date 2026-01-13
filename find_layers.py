import re

import requests

WFS_URL = "https://opendata.maps.vic.gov.au/geoserver/wfs"


def list_all_layers():
    print(f"Fetching capabilities from {WFS_URL}...")
    params = {"service": "WFS", "version": "1.1.0", "request": "GetCapabilities"}
    try:
        resp = requests.get(WFS_URL, params=params, timeout=60)  # Increased timeout
        content = resp.text

        # Regex to find <Name>...</Name> inside <FeatureType>
        # but simple regex for <Name>...</Name> is usually enough
        names = re.findall(r"<Name>(.*?)</Name>", content)

        # Filter out common non-layer names if any (like ows:...)
        layers = [n for n in names if ":" in n]  # Most layers are namespace:name

        print(f"Found {len(layers)} layers.")
        with open("layer_list.txt", "w") as f:
            for l in sorted(layers):
                f.write(l + "\n")
        print("Saved to layer_list.txt")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_all_layers()
    list_all_layers()
