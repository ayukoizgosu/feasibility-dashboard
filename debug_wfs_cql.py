import json

import requests
from rich.console import Console

console = Console()


def test_zone_intersects():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    # 2 Quamby Place, Donvale
    lat = -37.7849813
    lon = 145.1825641

    geom_cols = ["SHAPE", "the_geom", "geom", "geometry"]

    for col in geom_cols:
        console.print(f"\nTesting CQL INTERSECTS with column: {col}")

        cql = f"INTERSECTS({col}, POINT({lon} {lat}))"

        params = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": "open-data-platform:plan_zone",
            "outputFormat": "application/json",
            "cql_filter": cql,
            "maxFeatures": "5",
            "srsName": "EPSG:4326",
        }

        try:
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    features = data.get("features", [])
                    console.print(f"Features found: {len(features)}")
                    if features:
                        props = features[0].get("properties", {})
                        console.print(
                            f"Zone: {props.get('ZONE_CODE')} - {props.get('ZONE_DESC')}"
                        )
                        return  # Success!
                except Exception as e:
                    console.print(f"JSON Parse Error: {e}")
            else:
                console.print(f"Status: {resp.status_code}")
                console.print(resp.text[:200])

        except Exception as e:
            console.print(f"Request Error: {e}")


if __name__ == "__main__":
    test_zone_intersects()
    test_zone_intersects()
