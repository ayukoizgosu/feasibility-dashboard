import xml.etree.ElementTree as ET

import requests
from rich.console import Console

console = Console()


def list_target_layers():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetCapabilities",
    }

    console.print(f"Requesting capabilities from: {url}")

    try:
        resp = requests.get(url, params=params, timeout=30)
        console.print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                # Remove namespaces for easier parsing
                xml_str = resp.content.decode("utf-8")
                import re

                xml_str = re.sub(r' xmlns="[^"]+"', "", xml_str, count=1)
                # This simplistic removal might not be enough for all,
                # but let's try standard parsing with namespace map if needed.

                # Standard parsing
                root = ET.fromstring(resp.content)

                layer_names = []
                for elem in root.iter():
                    if elem.tag.endswith("Name"):
                        if elem.text and ":" in elem.text:
                            layer_names.append(elem.text)

                console.print(
                    f"\nFound {len(layer_names)} layers. Searching for 'zone' or 'plan'..."
                )

                relevant = [
                    n for n in layer_names if "zone" in n.lower() or "plan" in n.lower()
                ]

                for layer in sorted(set(relevant)):
                    console.print(f" - {layer}")

                console.print(
                    "\nChecking exact match for 'open-data-platform:plan_zone'..."
                )
                if "open-data-platform:plan_zone" in layer_names:
                    console.print("[green]FOUND 'open-data-platform:plan_zone'[/green]")
                else:
                    console.print("[red]NOT FOUND 'open-data-platform:plan_zone'[/red]")
            except Exception as e:
                console.print(f"XML Parsing Error: {e}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    list_target_layers()
    list_target_layers()
