import requests
from rich.console import Console

console = Console()


def describe_layer():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "DescribeFeatureType",
        "typeName": "open-data-platform:plan_zone",
    }

    console.print(f"Requesting schema from: {url}")

    try:
        resp = requests.get(url, params=params, timeout=30)
        console.print(f"Status: {resp.status_code}")
        console.print(resp.text[:2000])  # Print start of XSD

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    describe_layer()
