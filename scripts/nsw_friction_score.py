"""
NSW DA Friction Score Calculator
Connects to NSW Planning Open Data API, filters for Wollongong,
and calculates DA processing times (days lodged → determined).

Outputs:
  - data/wollongong_friction_data.csv   (raw DA records)
  - data/wollongong_friction_summary.json (aggregated stats for dashboard)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── Configuration ──────────────────────────────────────────────
# We try to discover the resource ID dynamically if this one fails.
RESOURCE_ID = "f01e16bc-c8ca-4feb-a99b-161ec347795c"
API_ROOT = "https://data.nsw.gov.au/data/api/3/action"
TARGET_LGA = "Wollongong City Council"
KILL_THRESHOLD_DAYS = 90
SAMPLE_LIMIT = 1000

# Output paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CSV_OUTPUT = DATA_DIR / "wollongong_friction_data.csv"
JSON_OUTPUT = DATA_DIR / "wollongong_friction_summary.json"


def find_resource_id() -> str | None:
    """Search for the correct resource ID via the CKAN API."""
    print("── Searching for 'Online DA Data' resource ID... ──")
    try:
        # Search for the package
        search_url = f"{API_ROOT}/package_search"
        params = {"q": "Online DA Data", "rows": 5}
        resp = requests.get(search_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            return None

        for package in data["result"]["results"]:
            # Check if title matches what we expect
            if (
                "Online DA Data" in package["title"]
                or "Development Application" in package["title"]
            ):
                print(f"Found package: {package['title']}")
                # Look for a datastore-active resource
                for res in package["resources"]:
                    # Prefer API-compatible resources
                    if res.get("datastore_active") or res["format"].upper() in [
                        "CSV",
                        "API",
                        "JSON",
                    ]:
                        print(f"Found candidate resource: {res['name']} ({res['id']})")
                        return res["id"]

        print("Could not find a suitable resource in search results.")
        return None

    except Exception as e:
        print(f"Discovery failed: {e}")
        return None


def fetch_da_records() -> pd.DataFrame | None:
    """Fetch DA records from the NSW Planning Portal API."""

    current_id = RESOURCE_ID

    # First attempt
    print(f"── Connecting to NSW Planning API for {TARGET_LGA} (ID: {current_id}) ──")
    df = _try_fetch(current_id)

    if df is not None:
        return df

    # If failed, try discovery
    print("Initial ID failed. Attempting discovery...")
    discovered_id = find_resource_id()
    if discovered_id and discovered_id != current_id:
        print(f"Retrying with discovered ID: {discovered_id}")
        return _try_fetch(discovered_id)

    print("All fetch attempts failed.")
    return None


def _try_fetch(resource_id: str) -> pd.DataFrame | None:
    try:
        url = f"{API_ROOT}/datastore_search"
        params = {
            "resource_id": resource_id,
            "q": TARGET_LGA,
            "limit": SAMPLE_LIMIT,
        }
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 404:
            print(f"Resource {resource_id} not found (404).")
            return None

        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            print(f"API Error: {data.get('error', 'Unknown error')}")
            return None

        records = data["result"]["records"]
        if not records:
            print("No records returned from API.")
            return None

        print(f"Fetched {len(records)} raw records.")
        return pd.DataFrame(records)

    except Exception as exc:
        print(f"Request failed: {exc}")
        return None


def calculate_friction(df: pd.DataFrame) -> pd.DataFrame | None:
    """Calculate days-to-process for determined DAs."""
    # Normalise column names
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Check required columns
    required = {"lodgement_date", "determination_date"}
    available = set(df.columns)
    if not required.issubset(available):
        print(f"Missing columns: {required - available}")
        return None

    # Parse dates
    df["lodgement_date"] = pd.to_datetime(df["lodgement_date"], errors="coerce")
    df["determination_date"] = pd.to_datetime(df["determination_date"], errors="coerce")

    # Keep only determined DAs
    determined = df.dropna(subset=["determination_date"]).copy()
    determined["days_to_process"] = (
        determined["determination_date"] - determined["lodgement_date"]
    ).dt.days

    # Filter invalid
    determined = determined[determined["days_to_process"] > 0]

    if determined.empty:
        print("No valid determined DAs found.")
        return None

    print(f"Analysed {len(determined)} determined DAs.")
    return determined


def build_summary(df: pd.DataFrame) -> dict:
    median_days = float(df["days_to_process"].median())
    mean_days = float(df["days_to_process"].mean())
    p90_days = float(df["days_to_process"].quantile(0.90))
    total_count = len(df)
    over_threshold = int((df["days_to_process"] > KILL_THRESHOLD_DAYS).sum())
    kill_status = "KILL" if median_days > KILL_THRESHOLD_DAYS else "GO"

    return {
        "lga": TARGET_LGA,
        "generated_at": datetime.now().isoformat(),
        "sample_size": total_count,
        "median_days": round(median_days, 1),
        "mean_days": round(mean_days, 1),
        "p90_days": round(p90_days, 1),
        "threshold_days": KILL_THRESHOLD_DAYS,
        "over_threshold_count": over_threshold,
        "over_threshold_pct": round(over_threshold / total_count * 100, 1),
        "kill_status": kill_status,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = fetch_da_records()
    if raw_df is None:
        sys.exit(1)

    friction_df = calculate_friction(raw_df)
    if friction_df is None:
        sys.exit(1)

    # Save CSV
    output_cols = [
        c
        for c in [
            "planning_portal_application_number",
            "full_development_description",
            "lodgement_date",
            "determination_date",
            "days_to_process",
        ]
        if c in friction_df.columns
    ]

    friction_df[output_cols].to_csv(CSV_OUTPUT, index=False)
    print(f"CSV saved → {CSV_OUTPUT}")

    # Save JSON summary
    summary = build_summary(friction_df)
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"JSON saved → {JSON_OUTPUT}")

    print(f"\n{'═' * 50}")
    print(f"  FRICTION SCORE (Median): {summary['median_days']} days")
    print(
        f"  Over {KILL_THRESHOLD_DAYS}d threshold: {summary['over_threshold_count']}/{summary['sample_size']} ({summary['over_threshold_pct']}%)"
    )
    print(f"  STATUS: {summary['kill_status']}")
    print(f"{'═' * 50}")


if __name__ == "__main__":
    main()
