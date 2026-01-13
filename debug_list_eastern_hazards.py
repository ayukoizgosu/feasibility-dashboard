"""
Debug script to list hazards in Eastern Suburbs.
"""

import xml.etree.ElementTree as ET

import requests
from rich.console import Console
from rich.table import Table

console = Console()
VICMAP_WFS_BASE = "https://opendata.maps.vic.gov.au/geoserver/wfs"


def parse_wfs_features(resp, label):
    """Try to parse JSON or GML."""
    if "json" in resp.headers.get("Content-Type", "").lower():
        try:
            return resp.json().get("features", [])
        except Exception:
            console.print(f"[red]JSON parse failed for {label}[/red]")
            return []

    # Try GML
    try:
        root = ET.fromstring(resp.text)
        features = []
        for member in root.iter():
            if "featureMember" in member.tag or "member" in member.tag:
                props = {}
                for child in member:
                    for elem in child:
                        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem.text:
                            props[tag] = elem.text.strip()
                if props:
                    features.append({"properties": props})
        return features
    except Exception as e:
        console.print(f"[red]GML parse failed for {label}: {e}[/red]")
        return []


def list_hazards():
    # Ringwood BBOX
    bbox = "145.10,-37.95,145.40,-37.70"

    layers = [
        ("EPA Priority Sites", "open-data-platform:psr_point"),
        ("EPA Sites (Licence)", "open-data-platform:epa_licence_point"),
        ("Enviro Audit Sites", "open-data-platform:enviro_audit_point"),
    ]

    for label, layer in layers:
        console.print(f"\n[bold]Querying {label}...[/bold]")

        # Try JSON first
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": layer,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "bbox": f"{bbox},EPSG:4326",
            "count": 100,
        }

        try:
            resp = requests.get(VICMAP_WFS_BASE, params=params, timeout=15)
            if resp.status_code != 200:
                console.print(f"[red]Error {resp.status_code}[/red]")
                continue

            features = parse_wfs_features(resp, label)
            console.print(f"Found {len(features)} features")

            landfill_candidates = []
            for f in features:
                props = f["properties"]
                # Search for keyword
                is_landfill = False
                for v in props.values():
                    if v and "landfill" in str(v).lower():
                        is_landfill = True
                        break

                if "landfill" in label.lower() or is_landfill:
                    landfill_candidates.append(props)

            if landfill_candidates:
                console.print(
                    f"[green]Found {len(landfill_candidates)} potential landfill records in {label}[/green]"
                )
                table = Table(title=f"Landfill Candidates ({label})")
                keys = list(landfill_candidates[0].keys())[:5]  # First 5 cols
                for k in keys:
                    table.add_column(k)
                for p in landfill_candidates[:20]:  # Show top 20
                    vals = [str(p.get(k, "")) for k in keys]
                    table.add_row(*vals)
                console.print(table)
            else:
                console.print(
                    f"No 'landfill' keywords found in {len(features)} records."
                )

        except Exception as e:
            console.print(f"[red]Request failed: {e}[/red]")


if __name__ == "__main__":
    list_hazards()
    list_hazards()
    list_hazards()
