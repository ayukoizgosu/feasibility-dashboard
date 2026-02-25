"""
ABS QuickStats Scraper
Fetches key demographics from the 2021 Census QuickStats page for a given LGA.

Usage:
    python scripts/connectors/abs_scraper.py <LGA_CODE>

Example:
    python scripts/connectors/abs_scraper.py LGA18450

Returns JSON with:
    - Population
    - Median Age
    - Median Household Income
    - Tertiary Education % (Bachelor or Higher)
    - Average Household Size
"""

import json
import re
import sys

import requests
from bs4 import BeautifulSoup


def scrape_abs_quickstats(lga_code):
    url = f"https://www.abs.gov.au/census/find-census-data/quickstats/2021/{lga_code}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {"error": f"Failed to fetch {url} (Status {r.status_code})"}

        soup = BeautifulSoup(r.content, "html.parser")
        data = {}

        # 1. Key Statistics (Top Table)
        # Usually found in the first table or summary box
        # Look for 'People' row

        # Helper to find value by row header
        def get_value(header_text):
            # Find th containing text
            th = soup.find("th", string=re.compile(header_text, re.IGNORECASE))
            if th:
                # Value is in the next td? Or same row next cell?
                # QuickStats tables: [Header] [Value]
                # Sometimes tr -> th, td
                tr = th.find_parent("tr")
                if tr:
                    tds = tr.find_all("td")
                    if tds:
                        return tds[0].text.strip().replace(",", "").replace("$", "")
            return None

        data["Pop_Current"] = get_value(r"^People$")
        data["Median_Age"] = get_value(r"Median age")
        data["Med_Household_Income"] = get_value(r"Median weekly household income")
        data["Avg_Household_Size"] = get_value(r"Average household size")

        # 2. Education (Bachelor or Higher)
        # Table: "Level of highest educational attainment"
        # Row: "Bachelor Degree level and above"
        # Column: Percentage for the region (1st data col usually?)
        # Let's verify table structure: Header row [Region, %, State, %, Aus, %]

        edu_heading = soup.find(
            string=re.compile(r"Level of highest educational attainment")
        )
        if edu_heading:
            # Find the table following this heading
            # The heading might be in a th or h2?
            # Usually h2 -> table
            table = None
            # Traverse parents to find container, then look for table?
            # Or strict search for table containing the text?
            for t in soup.find_all("table"):
                if t.find("th", string=re.compile("Bachelor Degree")):
                    table = t
                    break

            if table:
                row = table.find(
                    "th", string=re.compile("Bachelor Degree level and above")
                ).find_parent("tr")
                cols = row.find_all("td")
                if len(cols) > 1:
                    # Col 0 is Count, Col 1 is %
                    data["Tertiary_Quals_Pct"] = cols[1].text.strip().replace("%", "")

        # 3. Migration (Internal vs Overseas) is harder in QuickStats summary.
        # It's usually in "Country of birth" (Overseas born %)
        # "Top 5 countries of birth" table -> "Born in Australia" % -> rest is overseas?
        # Or "Person's place of usual residence 5 years ago" table?
        # "Same usual address" vs "Different usual address"

        return data

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No LGA code provided"}))
        sys.exit(1)

    lga = sys.argv[1]
    result = scrape_abs_quickstats(lga)
    print(json.dumps(result, indent=2))
    result = scrape_abs_quickstats(lga)
    print(json.dumps(result, indent=2))
