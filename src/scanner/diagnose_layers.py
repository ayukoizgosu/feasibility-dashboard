import re

import requests
from rich.console import Console

console = Console()


def search_layers():
    url = "https://opendata.maps.vic.gov.au/geoserver/wfs"
    params = {"request": "GetCapabilities", "service": "WFS"}

    console.print(f"[blue]Fetching capabilities from {url}...[/blue]")
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        text = resp.text

        console.print("[blue]Parsing layers...[/blue]")
        # Regex to find <Name>LayerName</Name>
        # Handles potential whitespace
        matches = re.findall(r"<Name>(.*?)</Name>", text, re.IGNORECASE)

        filtered = []
        for m in matches:
            m = m.strip()
            # Only keep layers with namespaces (e.g. open-data-platform:...)
            # And exclude generic OWS types like 'wfs:FeatureCollection'
            if (
                ":" in m
                and not m.startswith("wfs:")
                and not m.startswith("ows:")
                and not m.startswith("gml:")
            ):
                filtered.append(m)

        unique_layers = sorted(list(set(filtered)))

        # Dump to file
        with open("layers.txt", "w", encoding="utf-8") as f:
            for lyr in unique_layers:
                f.write(lyr + "\n")

        console.print(
            f"[green]Dumped {len(unique_layers)} unique layers to layers.txt[/green]"
        )

        # Keyword search
        keywords = [
            "hydro",
            "water",
            "road",
            "transport",
            "substation",
            "utility",
            "cemetery",
            "medical",
            "hospital",
            "emergency",
            "contour",
            "elevation",
            "parcel",
            "cadastre",
            "property",
        ]
        console.print(f"\n[bold]Searching for keywords: {keywords}[/bold]")

        for kw in keywords:
            hits = [l for l in unique_layers if kw.lower() in l.lower()]
            if hits:
                console.print(f"\n[cyan]{kw.upper()} ({len(hits)}):[/cyan]")
                for h in hits[:10]:
                    console.print(f" - {h}")
                if len(hits) > 10:
                    console.print(f"   ... and {len(hits)-10} more")
            else:
                console.print(f"\n[dim]{kw.upper()}: No matches[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    search_layers()
    search_layers()
