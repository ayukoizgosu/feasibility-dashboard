"""
Generate Data Exports for Market Analysis

Mirrors the logic in market_scan.html (JS) to produce CSV snapshots
for key analysis points:
1. Full Dataset (Enriched with Kill/Priority)
2. High Priority Opportunities
3. GO Status Only
4. Wollongong Deep Dive
5. Competition Summary
"""

import re
from pathlib import Path

import pandas as pd

# ── Config ─────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXPORT_DIR = DATA_DIR / "exports"
INPUT_CSV = DATA_DIR / "market_scan_data.csv"


# ── Logic (Mirrors JS) ─────────────────────────────────────────
def clean_growth(val):
    try:
        if pd.isna(val) or val == "N/A":
            return None
        return float(val)
    except:
        return None


def assign_priority(row):
    gr = clean_growth(row.get("Growth_Rate"))
    if gr is None:
        return "Medium"
    if gr >= 0.02:
        return "High"
    if gr >= 0:
        return "Medium"
    return "Low"


def compute_kill_status(row):
    val = str(row.get("Value", ""))
    gr = clean_growth(row.get("Growth_Rate"))
    tab = row.get("Tab")

    # 1. Check DA Time > 90 days
    days_match = re.search(r"(\d+)\s*[Dd]ays", val)
    if days_match:
        days = int(days_match.group(1))
        if days > 90:
            return "KILL", 0, f"DA {days}d > 90d"

    # 2. Check Yield < 4% (Feasibility only)
    if tab == "Feasibility" and gr is not None and gr < 0.04:
        return "KILL", 0, f"Yield {gr*100:.1f}% < 4%"

    # 3. Calculate Score
    if gr is not None:
        base = gr + (gr if gr > 0 else 0)
        score = round(base * 100)
        return "GO", max(score, 1), ""

    return "GO", "-", ""


# ── Main ───────────────────────────────────────────────────────
def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Load Data
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"Error: {INPUT_CSV} not found.")
        return

    # Enrich Data
    df["Priority"] = df.apply(assign_priority, axis=1)

    kill_results = df.apply(compute_kill_status, axis=1)
    df["Kill_Status"] = [x[0] for x in kill_results]
    df["Kill_Score"] = [x[1] for x in kill_results]
    df["Kill_Reason"] = [x[2] for x in kill_results]

    # ── Export 1: Full Scan (Market Overview) ──────────────────
    feature_cols = [
        "Tab",
        "Region",
        "Metric",
        "Value",
        "Growth_Rate",
        "Source",
        "Notes",
        "Priority",
        "Kill_Status",
        "Kill_Score",
        "Kill_Reason",
    ]
    full_df = df[feature_cols]
    full_df.to_csv(EXPORT_DIR / "01_Full_Market_Scan.csv", index=False)
    print("✅ Exported: 01_Full_Market_Scan.csv")

    # ── Export 2: High Priority (Growth Targets) ───────────────
    high_pri = full_df[full_df["Priority"] == "High"]
    high_pri.to_csv(EXPORT_DIR / "02_High_Growth_Priority.csv", index=False)
    print("✅ Exported: 02_High_Growth_Priority.csv")

    # ── Export 3: GO Status (Qualified Opportunities) ──────────
    go_status = full_df[full_df["Kill_Status"] == "GO"]
    go_status.to_csv(EXPORT_DIR / "03_GO_Status_Opportunities.csv", index=False)
    print("✅ Exported: 03_GO_Status_Opportunities.csv")

    # ── Export 4: Wollongong Deep Dive ─────────────────────────
    wollongong = full_df[full_df["Region"] == "Wollongong"]
    wollongong.to_csv(EXPORT_DIR / "04_Wollongong_Deep_Dive.csv", index=False)
    print("✅ Exported: 04_Wollongong_Deep_Dive.csv")

    # ── Export 5: Competition Summary ──────────────────────────
    competition = full_df[full_df["Tab"] == "Competition"]
    competition.to_csv(EXPORT_DIR / "05_Competition_Summary.csv", index=False)
    print("✅ Exported: 05_Competition_Summary.csv")


if __name__ == "__main__":
    main()
    main()
