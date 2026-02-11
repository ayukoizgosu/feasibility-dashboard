import re
from pathlib import Path

import pandas as pd

REPORT_PATH = Path("reports/dual_occ_candidates.csv")


def clean_address_from_url(url):
    try:
        # Example: https://www.domain.com.au/5-dellwood-court-templestowe-vic-3106-2020402665
        if not isinstance(url, str):
            return None

        # Split by domain
        parts = url.split("www.domain.com.au/")[-1].split("?")[0]

        # Remove ID at end (last numeric sequence after dash)
        # But some addresses end in numbers, so be careful.
        # Domain format usually: address-suburb-state-postcode-listingID

        # safely split by hyphens
        segments = parts.split("-")

        # If the last segment is purely numeric and long (listing ID), drop it
        if segments[-1].isdigit() and len(segments[-1]) > 6:
            segments = segments[:-1]

        # Rejoin and Title Case
        slug = " ".join(segments)
        return slug.title()
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        return None


def clean_duplicates():
    if not REPORT_PATH.exists():
        print("Report not found.")
        return

    print(f"Reading {REPORT_PATH}...")
    df = pd.read_csv(REPORT_PATH)
    print(f"Original count: {len(df)}")

    # Clean Addresses
    fixed_count = 0
    for idx, row in df.iterrows():
        addr = str(row["address"])

        # Heuristic: If address looks like a name (no digits) or matches known bad patterns
        # Or if it came from the scraping bug (e.g. "Values", "Sold", Agent Name)
        # Or if it contains a price symbol "$"
        is_suspicious = False
        if not any(c.isdigit() for c in addr):
            is_suspicious = True
        if "$" in addr:
            is_suspicious = True

        if is_suspicious:
            new_addr = clean_address_from_url(row["url"])
            if new_addr:
                # Only update if new address looks better (has digits, no $)
                if any(c.isdigit() for c in new_addr) and "$" not in new_addr:
                    print(f"Fixing '{addr}' -> '{new_addr}'")
                    df.at[idx, "address"] = new_addr
                    fixed_count += 1

    # Deduplicate
    df.drop_duplicates(subset=["address"], keep="last", inplace=True)

    print(f"Fixed {fixed_count} addresses.")
    print(f"Final unique count: {len(df)}")

    df.to_csv(REPORT_PATH, index=False)
    print("Saved clean report.")


if __name__ == "__main__":
    clean_duplicates()
