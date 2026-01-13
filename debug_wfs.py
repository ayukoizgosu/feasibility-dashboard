import json

import requests
from rich.console import Console

console = Console()


def test_zone_layer():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    # 2 Quamby Place, Donvale
    bbox = "145.182, -37.786, 145.183, -37.784"  # Lon,Lat ~100m box

    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:plan_zone",
        "outputFormat": "application/json",
        "bbox": bbox,
        "maxFeatures": "5",
        "srsName": "EPSG:4326",
    }

    console.print(f"Requesting: {url}")
    console.print(f"Params: {json.dumps(params, indent=2)}")

    try:
        resp = requests.get(url, params=params, timeout=10)
        console.print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                data = resp.json()
                features = data.get("features", [])
                console.print(f"Features: {len(features)}")
                if features:
                    console.print(json.dumps(features[0]["properties"], indent=2))
                else:
                    console.print("[yellow]No features found in bbox[/yellow]")
            except Exception as e:
                console.print(f"JSON Parse Error: {e}")
                console.print(resp.text[:500])
        else:
            console.print(resp.text[:500])

    except Exception as e:
        console.print(f"Request Error: {e}")


if __name__ == "__main__":
    test_zone_layer()
    test_zone_layer()
