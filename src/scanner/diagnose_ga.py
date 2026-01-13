import re

import requests
from rich.console import Console

console = Console()


def search_ga():
    # GA National Electricity Infrastructure
    url = "https://services.ga.gov.au/gis/services/National_Electricity_Infrastructure/MapServer/WFSServer"
    params = {"request": "GetCapabilities", "service": "WFS", "version": "1.1.0"}

    console.print(f"[blue]Fetching GA capabilities from {url}...[/blue]")
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        text = resp.text

        console.print("[blue]Parsing layers...[/blue]")
        # WFS 1.1.0 usually uses <Name> or <FeatureType><Name>
        # We grab anything that looks like a layer name
        # GA convention: Namespace:LayerName

        # Method 1: Regex
        matches = re.findall(r"<Name>(.*?)</Name>", text)
        filtered = sorted(
            list(set([m for m in matches if ":" in m or "Electricity" in m]))
        )

        if filtered:
            console.print(f"[green]Found {len(filtered)} potential layers:[/green]")
            for lyr in filtered:
                console.print(f" - {lyr}")
        else:
            console.print(
                "[yellow]No obvious layers found with regex. Dumping raw Name tags:[/yellow]"
            )
            for m in matches[:20]:
                console.print(f" - {m}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    search_ga()
    search_ga()
