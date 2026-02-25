"""
Market Scan Data Ingestion Engine
Updates the market scan CSV with live data from configured connectors.

Currently supported connectors:
- ABS QuickStats (Demographics via LGA code)

Usage:
    python scripts/update_market_scan.py
"""

import os
import sys
import time

import pandas as pd

# Ensure we can find the connectors module
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Ensure Cwd is project root (parent of scripts/)
project_root = os.path.dirname(script_dir)
if os.getcwd() != project_root:
    try:
        os.chdir(project_root)
        print(f"Changed directory to: {project_root}")
    except Exception as e:
        print(f"Warning: Could not change directory to {project_root}: {e}")

from connectors import abs_scraper

# Configuration
INPUT_FILE = "data/market_scan_v2_template.csv"
OUTPUT_FILE = "data/market_scan_v2_live.csv"


def update_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # Columns to update from ABS
    abs_map = {
        "Pop_Current": "Pop_Current",
        "Median_Age": "Median_Age",
        "Med_Household_Income": "Med_Household_Income",
        "Tertiary_Quals_Pct": "Tertiary_Quals_Pct",
        # 'Avg_Household_Size': 'Avg_Household_Size' # Add to schema if needed
    }

    # Iterate rows
    for index, row in df.iterrows():
        region_id = str(row["Region_ID"])

        # ABS Connector
        if region_id.startswith("LGA"):
            print(f"[{region_id}] Fetching ABS Data...")
            try:
                data = abs_scraper.scrape_abs_quickstats(region_id)

                if "error" in data:
                    print(f"  Warning: {data['error']}")
                else:
                    changes = []
                    for schema_col, abs_key in abs_map.items():
                        if abs_key in data and data[abs_key]:
                            old_val = row[schema_col]
                            new_val = data[abs_key]
                            df.at[index, schema_col] = new_val
                            changes.append(f"{schema_col}: {old_val} -> {new_val}")

                    print(f"  Updated {len(changes)} fields.")

            except Exception as e:
                print(f"  Error running ABS scraper: {e}")

            # Rate limit politely
            time.sleep(1)

    print(f"Saving updated data to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    print("Done.")


if __name__ == "__main__":
    # Ensure script can find connectors
    sys.path.append(os.path.join(os.path.dirname(__file__)))
    update_data()
    update_data()
