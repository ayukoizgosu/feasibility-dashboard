import json

import requests
from rich.console import Console

console = Console()


def test_coords():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    lat = -37.7849813
    lon = 145.1825641

    variations = [
        ("Lon Lat", f"POINT({lon} {lat})", "EPSG:4326"),
        ("Lat Lon", f"POINT({lat} {lon})", "EPSG:4326"),
        ("Lon Lat GDA94", f"POINT({lon} {lat})", "EPSG:4283"),
    ]

    for label, point, srs in variations:
        console.print(f"\nTesting: {label} -> {point} ({srs})")

        cql = f"INTERSECTS(geom, {point})"

        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": "open-data-platform:plan_zone",
            "outputFormat": "application/json",
            "cql_filter": cql,
            "maxFeatures": "5",
            "srsName": srs,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                console.print(f"Features: {len(features)}")
                if features:
                    props = features[0].get("properties", {})
                    console.print(f"MATCH! Zone: {props.get('zone_code')}")
                    return
            else:
                console.print(f"Status: {resp.status_code}")
                # console.print(resp.text[:200])
        except Exception as e:
            console.print(f"Error: {e}")


if __name__ == "__main__":
    test_coords()
    test_coords()
