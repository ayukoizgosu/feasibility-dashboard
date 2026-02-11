---
description: Scan a property address for development feasibility (LDRZ subdivision focus)
---

# Property Scan Workflow

Follow this process exactly when asked to "scan property" or "assess feasibility".

1. **Parse Address**
   - Extract the full address from the user request.
   - If suburb is missing, ask for clarification or infer from context (e.g. "Donvale", "Park Orchards").

2. **Geocode Address**
   - Run `src/scanner/scan_single.py` with the address.
   - Example: `poetry run python src/scanner/scan_single.py "1 Lookover Drive, Donvale"`

3. **Interpret "Quick Kill" Results**
   - The script runs automated checks. Review the output for:
     - **Transmission Lines**: Is it >300m away? (REJECT if <300m)
     - **Substations**: Is it >200m away? (REJECT if <200m)
     - **EPA Priority Sites**: Are there contamination sites nearby? (REJECT if <500m)
     - **Planning Overlays**: Are there hard blockers like PAO, EAO, or Heritage (HO)?
     - **Bushfire Prone Area (BPA)**: Note this adds construction cost but is usually not a hard blocker.

4. **Interpret "Deep Dive" Results** (if Quick Kill passed)
   - **Zoning**: Is it LDRZ? (Critical for this workflow)
   - **Lot Size**: Is it >4000sqm? (Needed for 2 lots)
   - **Slope**: Is average slope <15%? (Steep sites = high cost)
   - **Sewerage**: Is reticulated sewer available? (Yarra Valley Water check)
     - If NO sewer, min lot size is usually ~4000sqm (0.4ha).
     - If YES sewer, min lot size can be 2000sqm (0.2ha) in some schedules.

5. **Review Feasibility Financials**
   - **Margin**: Is it >20%?
   - **Profit**: Is it >$250k?
   - **ROE**: Is it >15%?

6. **Present Recommendation**
   - **GO**: Clear pass on all checks, margin >20%.
   - **MARGINAL**: Passes checks but margin 10-20% or has issues (slope, irregular shape).
   - **NO GO**: Failed quick kill or negative margin.

---

## Command Reference

Run single scan:
```bash
poetry run python src/scanner/scan_single.py "{ADDRESS}"
```

Run batch scan (if multiple addresses provided):
```bash
poetry run python run_new_candidates.py
```

## Stealth Discovery & Ingestion (VPN + Rotation)

To find **new** candidates by scraping Domain and RealEstate.com.au with VPN rotation:

```bash
# Runs 5 batches, rotating VPN location and Source (Domain/REA) each time for stealth
python scripts/run_with_vpn.py --loops 5
```

**Note:** This script automatically:
1. Disconnects/Connects ExpressVPN to random Australian locations.
2. Rotates between 'domain' and 'rea' sources (or both) to avoid blocking.
3. Scrapes listings and filters for LDRZ candidates.
4. Generates a report in `reports/weekly_ldrz_candidates_latest.csv`.
