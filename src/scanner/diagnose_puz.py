import requests
from rich.console import Console

console = Console()


def check_zone_codes():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    # Just get a few zones
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": "open-data-platform:plan_zone",
        "outputFormat": "application/json",
        "maxFeatures": 50,
        "srsName": "EPSG:4326",
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        features = data.get("features", [])

        codes = set()
        for f in features:
            p = f["properties"]
            codes.add(f"{p.get('zone_code')} ({p.get('zone_description')})")

        console.print("[blue]Sample Zone Codes:[/blue]")
        for c in sorted(list(codes)):
            console.print(f" - {c}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    check_zone_codes()
