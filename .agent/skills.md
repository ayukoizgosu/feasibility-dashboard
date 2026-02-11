# Site Scanner Skills & Lessons Learned

## Critical Analysis Rules

### 1. ALWAYS Verify Yield Before Calculating Profitability

**Lesson Learned (Jan 2026):** When analyzing a development site, I assumed 2 townhouses were built on a sample property based on typical dual-occ expectations for an 846sqm block. The actual development was **3 townhouses**, fundamentally changing the profitability calculation.

**Rule:** Before calculating feasibility:

1. Search for ALL unit addresses at the property (1/XX, 2/XX, 3/XX, etc.)
2. Verify each unit's sale history independently
3. Never assume yield based on land size alone - always verify actual outcome

**Verification Method:**

```
Search query: "[address] units 1/[number] 2/[number] 3/[number] sold"
Search query: "[address] all units addresses how many townhouses"
```

---

### 2. Account for Common Property in Subdivisions

**Lesson Learned (Jan 2026):** Original lot was 846sqm, but subdivided lots only totaled 621sqm. The 225sqm difference (27%) was **common property** for shared driveway/accessway.

**Rule:** When analyzing multi-unit developments:

1. Sum all individual lot sizes from search results
2. If total < original lot size, the difference is likely common property
3. Common property typically 15-30% of original lot for 3+ unit developments
4. Common property includes: shared driveway, visitor parking, turning areas, utility easements

**Impact on Analysis:**

- Common property generates NO additional revenue (not saleable separately)
- Costs are included in subdivision fees
- Reduces effective land per unit (affects density calculations)

---

### 3. Property Comparable Sales Methodology

When calculating GDV (Gross Development Value):

1. **Use actual comparable sales** from the same suburb
2. **Match product type** (3-bed townhouse vs 4-bed townhouse)
3. **Consider internal size** - price per sqm varies by location
4. **Check timing** - prices change significantly over years
5. **Verify number of units** via search before calculating totals
6. **Get individual unit prices** - don't assume all units sell for same price

---

### 4. Land Size vs Yield Relationship

General guidelines (Melbourne, may vary):

| Land Size (sqm) | Typical Yield | Common Property % |
|-----------------|---------------|-------------------|
| 500-600 | 2 units | 15-20% |
| 600-800 | 2-3 units | 20-25% |
| 800-1000 | 3-4 units | 25-30% |
| 1000+ | 4+ units | 25-35% |

**Warning:** These are guidelines only. Always verify actual development outcome.

---

### 5. Finance Rate Selection

| Dwelling Count | Rate Type | Typical Rate (2024) |
|----------------|-----------|---------------------|
| 1-3 dwellings | Residential mortgage | 6.5% @ 80% LVR |
| 4+ dwellings | Commercial construction | 8.5% @ 70% LVR |
| Equity shortfall | Mezzanine debt | 12-18% p.a. |

---

### 6. Self-Verification Before Presenting Results

**Lesson Learned (Jan 2026):** User had to point out that I assumed 2 townhouses without verification. I should have caught this myself.

**Rule:** Before presenting ANY feasibility analysis:

1. Explicitly state what I'm about to verify
2. Run ALL verification searches in the first pass (not after user questions)
3. Cross-check totals (do land sizes add up? do costs make sense?)
4. Flag any discrepancies or unknowns prominently
5. Never present incomplete analysis as complete

**Self-Check Questions:**

- [ ] Did I search for ALL unit addresses (not just assume count)?
- [ ] Did I verify sale price for EACH unit individually?
- [ ] Do the land sizes of subdivided lots add up to original? If not, why?
- [ ] Did I use period-appropriate cost data (not current rates for historical deals)?
- [ ] Have I cross-referenced at least 2 sources for key figures?

---

### 7. Common Assumption Errors to Avoid

1. ❌ **Assuming yield from land size** → Always verify actual units built
2. ❌ **Using hardcoded sale prices** → Use recent comparable sales
3. ❌ **Ignoring timing** → Prices change; use period-appropriate data
4. ❌ **Single source verification** → Cross-check multiple sources
5. ❌ **Ignoring unit variations** → Different configs = different prices
6. ❌ **Forgetting common property** → Multi-unit developments have shared areas
7. ❌ **Assuming all units sell for same price** → Verify each unit's sale
8. ❌ **Presenting analysis without complete verification** → Verify FIRST, present SECOND

---

### 8. Historical Analysis Considerations

When analyzing past deals (e.g., "what if you bought in 2018"):

1. Use historical construction costs (not current rates)
2. Use historical interest rates (check RBA cash rate + typical margin)
3. Consider holding period if sold years later
4. Account for market appreciation/depreciation
5. Acknowledge if some data is estimated vs verified

---

## Data Verification Checklist

Before presenting feasibility analysis:

- [ ] Verified number of units via multiple search queries
- [ ] Found sale price for EACH unit individually
- [ ] Confirmed land sizes add up (identified common property if not)
- [ ] Confirmed construction costs are period-appropriate
- [ ] Cross-referenced land size with parcel data
- [ ] Checked zoning constraints (NRZ limits, overlays)
- [ ] Verified frontage (impacts yield potential)
- [ ] Flagged any assumptions or unknowns explicitly
- [ ] Double-checked math (GDV, TDC, profit, margin)

---

## Automation Goals

When user requests "be automated" or "don't rely on me":

1. Run ALL verification searches upfront without prompting
2. Cross-check data from multiple sources
3. Flag discrepancies rather than assuming
4. Present complete analysis with verification notes
5. Only ask user for input on genuine unknowns

---

---

## 19. Address Consolidation Risk (Data Discrepancies)

**Lesson Learned (Jan 2026):**
A scan of "26 Heads Road, Donvale" returned a land size of 12,329sqm. The real estate listing was for ~4,000sqm.
**Why?** The geocoder resolved "26 Heads Road" to the parent title's address range "22-26 Heads Road", and the WFS query returned the *entire consolidated parcel* geometry.

**Rule:**

1. **Check Geocoded Address:** If input is "26" but found is "22-26", the area is likely for the whole group.
2. **Verify vs Listing:** If GIS area is >150% of listing area (or implied area), assume it's a consolidated title or neighbouring parcels are merged.
3. **Visual Check:** Look at the shape. Does 12,000sqm look like 3 blocks? (Yes).

**Correction:**
When this happens, manually override the area or divide by the lot count if known (e.g., 3 lots).

---

## Case Study: Example Development (Real Deal)

### Timeline (Actual)

| Phase | Date | Duration |
|-------|------|----------|
| Purchase | March 2018 | - |
| COVID funding delays | 2020-2021 | ~24 months |
| Construction start | Feb 2022 | - |
| Construction finish | Oct 2023 | 20 months |
| Unit 1 sold | Dec 2024 | - |
| Unit 2 sold | Jun 2025 | - |
| **Total holding** | **~7 years** | - |

### Actual Costs (User-Provided)

- Land: $1,160,000
- Demolition (cash): $15,000
- Construction (inc. site works): $1,200,000
- Finance (80% drawdown, 7yr): ~$790,000

### Tax Strategy Applied

- **PPR (Principal Place of Residence)**: Developer lived in property to demonstrate PPR status
- **Benefit**: Avoid GST on sale + CGT exemption/discount
- **Trade-off**: Extended holding increases finance costs

### Key Lesson

**Finance costs compound over time** - 7-year hold cost ~$790K in interest, eating most of the profit that quick-flip would have captured.

---

## 9. Holding Period Risk & Finance Cost Compounding

**Lesson Learned (Jan 2026):** Real deal showed 7-year hold (due to COVID + PPR strategy) cost ~$790K in finance vs ~$142K for 18-month flip. This changed margin from ~28% to ~3%.

**Rule:** Always model multiple holding scenarios:

| Holding Period | Finance Cost Impact |
|----------------|---------------------|
| 12-18 months | Base case |
| 24-36 months | +100% finance cost |
| 48+ months | Finance may exceed profit |

**Formula:**

```
Finance Cost = (Land + Construction) × Interest Rate × (Months/12) × Drawdown%
```

**Example (Case Study):**

- Quick flip (18mo): $2.36M × 5% × 1.5 × 80% = $142K
- Actual (84mo): $2.36M × 5% × 7 × 80% = $790K

---

## 10. Tax Strategies That Affect Hold Period

### PPR (Principal Place of Residence) Strategy

- **Purpose**: Avoid GST on sale + CGT exemption
- **Requirement**: Live in property as main residence
- **Duration**: Usually 12+ months per unit
- **Trade-off**: Extended hold = higher finance costs
- **Best for**: When tax savings > additional finance costs

### GST Margin Scheme

- **Standard**: GST = (GDV - Land Cost) / 11
- **Margin Scheme**: GST = (Sale Price - Purchase Price) / 11
- **Benefit**: Lower GST if property appreciated

### CGT Considerations

- **<12 months**: Full CGT (no discount)
- **>12 months**: 50% CGT discount (individuals)
- **PPR exemption**: No CGT if main residence

---

## 11. Construction Delay Factors

When estimating construction timeline, add contingency for:

1. **Council approvals** (+2-6 months)
2. **Builder availability** (+1-3 months)
3. **Weather delays** (+1-2 months)
4. **Supply chain issues** (+3-6 months, esp. post-COVID)
5. **Funding approval delays** (+2-12 months if COVID/market disruption)

**Real example**: A sample project waited ~4 years (2018-2022) before construction started due to COVID funding delays.

---

## Updated Feasibility Model Requirements

When building feasibility calculators:

1. **Model multiple holding scenarios** (12mo, 24mo, 36mo, 48mo+)
2. **Show finance cost sensitivity** to holding period
3. **Flag if finance cost > 30% of development margin**
4. **Include tax strategy options** (PPR, margin scheme, CGT timing)
5. **Use realistic drawdown** (80% for construction, not 60%)
6. **ALWAYS include stamp duty** in acquisition costs
7. **Calculate ROE** (Return on Equity) not just margin on TDC

---

## 12. Stamp Duty (Critical - Don't Forget!)

**Lesson Learned (Jan 2026):** I forgot to include stamp duty in the original analysis. For a $1.16M purchase, this was ~$64K - a significant cost.

**Victorian Stamp Duty Rates (2024):**

| Property Value | Rate |
|----------------|------|
| $0 - $25,000 | 1.4% |
| $25,001 - $130,000 | 2.4% |
| $130,001 - $960,000 | 5.0% |
| $960,001+ | 5.5% |

**Quick Estimate:** ~5.5% of purchase price for properties over $1M

**Example (Case Study):**

- Purchase: $1,160,000
- Stamp duty: ~$63,800
- **This is 100% cash outlay** (cannot be financed)

---

## 13. Return on Equity (ROE) Calculation

**Why ROE matters more than margin:**

- Margin on TDC shows overall deal quality
- ROE shows return on YOUR ACTUAL CASH invested
- Most developments use 70-80% debt, so ROE amplifies returns

**Formula:**

```
Total ROE = Net Profit / Cash Invested × 100%
Annualized ROE = (1 + Total ROE)^(1/Years) - 1
```

**Cash Required Components:**

| Phase | Cash Items |
|-------|------------|
| Purchase | Deposit (20%) + Stamp duty + Legals |
| Pre-construction | Demolition + Design fees + Holding costs |
| Construction | Builder deposit (5-10%) + Interest shortfall |
| Sales | Marketing + Final interest shortfall |

**Example (Case Study):**

- Cash invested: $584K
- Profit: $451K (tax-free via PPR)
- Total ROE: 77%
- Annualized ROE: 8.3% p.a.

**Benchmark ROE Targets:**

| Holding Period | Min Annualized ROE |
|----------------|-------------------|
| 12-18 months | 50%+ |
| 24-36 months | 25%+ |
| 48+ months | 15%+ |

---

## 14. Complete Cost Checklist

**Acquisition Costs (Cash):**

- [ ] Deposit (20% of land)
- [ ] Stamp duty (~5.5%)
- [ ] Legals/conveyancing ($2-5K)
- [ ] Due diligence (surveys, searches)

**Pre-Development (Cash/Finance):**

- [ ] Demolition
- [ ] Town planning fees
- [ ] Architect design
- [ ] Engineering
- [ ] Council application fees

**Construction (Financed @ 70-80%):**

- [ ] Builder contract
- [ ] Site works (often included)
- [ ] Landscaping
- [ ] Driveways/crossovers

**Soft Costs (Financed):**

- [ ] Professional fees (10%)
- [ ] Contingency (7.5%)
- [ ] Statutory (2%)

**Finance Costs:**

- [ ] Interest during land holding
- [ ] Interest during construction (80% drawdown)
- [ ] Interest post-completion until sale

**Sales Costs:**

- [ ] Agent commission (1.5%)
- [ ] Marketing/staging (~$10-20K)
- [ ] Conveyancing per sale

**Tax (unless PPR):**

- [ ] GST (margin scheme or standard)
- [ ] CGT (if applicable)

---

## Case Study Financial Summary: Example Development

| Item | Amount |
|------|--------|
| Land | $1,160,000 |
| Stamp Duty | $63,800 |
| Demolition | $15,000 |
| Construction | $1,200,000 |
| Prof Fees | $120,000 |
| Contingency | $90,000 |
| Statutory | $24,000 |
| Finance (7yr) | $622,667 |
| Selling | $57,060 |
| **TDC** | **$3,352,527** |
| **GDV** | **$3,804,000** |
| **Profit** | **$451,473** |
| Cash Required | $583,800 |
| **ROE** | **77.3%** |
| **Annualized** | **8.3% p.a.** |

---

## 15. LDRZ Subdivision Strategy (Highest ROE)

**Discovered (Jan 2026):** Low Density Residential Zone (LDRZ) subdivision offers the highest risk-adjusted ROE of all strategies analyzed.

### The Opportunity

| Sewerage Status | Minimum Lot Size |
|-----------------|------------------|
| NO reticulated sewerage | 4,000 sqm (0.4 ha) |
| WITH reticulated sewerage | **2,000 sqm (0.2 ha)** ✓ |

**Arbitrage:** Buy 4,000+ sqm LDRZ @ ~$400-500/sqm → Subdivide → Sell 2 × 2,000sqm @ ~$550-700/sqm

### Target Suburbs (Manningham LDRZ)

| Suburb | Land $/sqm | Sewerage likely? |
|--------|-----------|------------------|
| Donvale | $400-580 | Yes (most areas) |
| Park Orchards | $300-500 | Check each property |
| Templestowe | $500-700 | Yes (most areas) |
| Warrandyte | $350-500 | **Often NO - check!** |

### Quick Feasibility

```
Buy:    4,000 sqm @ $1.8M ($450/sqm)
Costs:  $200K (stamp duty + subdivision + holding)
Sell:   2 × 2,000 sqm @ $1.2M each = $2.4M
Profit: ~$350-400K
ROE:    ~50%+ (12 months)
```

---

## 16. Infrastructure Due Diligence Checklist

### CRITICAL: Check Before Buying LDRZ Block

**1. Reticulated Sewerage (MOST IMPORTANT)**

- Call: **Yarra Valley Water 1300 304 688**
- Ask: "Is [address] connected to reticulated sewerage?"
- Get written confirmation
- ⚠️ If NO sewer: Can only subdivide to 4,000sqm minimum (not 2,000sqm)

**2. Transmission Lines (HIGH VOLTAGE)**

- Check: **Geoscience Australia electricity data** (Site Scanner has this built-in)
- Setback requirements:

  | Voltage | Minimum Setback |
  |---------|-----------------|
  | 66kV | ~20m from centre |
  | 132kV | ~30m from centre |
  | 220kV | ~40m from centre |
  | 330kV+ | ~50m+ from centre |

- ⚠️ Easements can consume 20-60m width of land = unusable for building

**3. Zoning Confirmation**

- Check: **VicPlan** (planning.vic.gov.au)
- Confirm zone is LDRZ
- Check for schedules that may vary minimum lot size

**4. Overlays**

- Check for:
  - ESO (Environmental Significance Overlay)
  - SLO (Significant Landscape Overlay)
  - VPO (Vegetation Protection Overlay)
  - BMO (Bushfire Management Overlay)
- Any overlay may restrict subdivision or add costs

**5. Title Search (via LANDATA)**

- Check for:
  - Restrictive covenants (may prevent subdivision)
  - Easements (powerlines, sewers, drainage)
  - Caveats
  - Section 173 agreements

**6. Frontage & Access**

- Minimum frontage: ~15m per lot (check council)
- Battle-axe lots may have reduced frontage requirements
- Check if rear lot can access via driveway

**7. Slope & Drainage**

- Steep blocks = expensive civil works
- Check for natural drainage lines
- May need retention systems

---

## 17. Transmission Line Setbacks

**Why This Matters:**
High-voltage powerlines create easements that restrict development. A 66kV line can consume 40m width of your block.

**Setback Guidelines (Victorian regulations):**

| Voltage | Easement Width | Building Setback |
|---------|---------------|-----------------|
| 22kV | 10-15m | 5m from conductor |
| 66kV | 20-30m | 10m from conductor |
| 132kV | 30-40m | 15m from conductor |
| 220kV | 40-50m | 20m from conductor |
| 500kV | 60-80m | 30m from conductor |

**Impact Example:**

- 4,000sqm block with 220kV line through middle
- Easement: 50m wide × 100m long = 5,000sqm unusable!
- May prevent subdivision entirely

**How to Check:**

1. Use Site Scanner's transmission line cache (already built-in)
2. Check AusGrid/Transmission operator maps
3. Look for tall pylons on Google Street View
4. Get title search for registered easements

---

## 18. LDRZ vs GRZ Comparison

| Factor | LDRZ | GRZ |
|--------|------|-----|
| Land $/sqm | $350-600 | $1,200-2,000+ |
| Minimum lot (with sewer) | 2,000sqm | 300-500sqm |
| Yield per hectare | 5 lots | 20-30 lots |
| Competition | LOW | HIGH |
| Complexity | LOW | MEDIUM-HIGH |
| Finance type | Residential | Often commercial |
| Best strategy | Subdivision only | Build + sell |

**Key Insight:** LDRZ works because you're arbitraging the land price, not the building value.

---

## Strategy Comparison Summary

| Strategy | Suburb | Cash | Profit | Ann.ROE | Risk |
|----------|--------|------|--------|---------|------|
| **LDRZ Subdiv Only** | Donvale | **$465K** | $244K | **52.4%** | **LOW** |
| 3 TH (PPR) | Donvale | $584K | $451K | 8.3%* | LOW |
| 8 Townhouses | Eltham | $1.8M | $582K | 15.0% | HIGH |
| 3 Townhouses | Balwyn | $1.1M | $210K | 10.9% | MED |
| 1 Mansion | Balwyn | $1.15M | $168K | 8.4% | HIGH |

*Tax-free (PPR equivalent ~12%)

**Winner:** LDRZ Subdivision in Donvale/Park Orchards with sewerage connection

---

## 20. Water Utility API Endpoints (Sewerage Verification)

### Melbourne Water (Trunk Mains)

**Endpoints (ArcGIS FeatureServer):**

```
# Sewer Mains
https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/Sewerage_Network_Mains/FeatureServer/0

# Water Supply Mains
https://services5.arcgis.com/ZSYwjtv8RKVhkXIL/arcgis/rest/services/Water_Supply_Main_Pipelines/FeatureServer/0
```

**GeoJSON Query Pattern:**

```
/query?where=1%3D1&geometry={minX},{minY},{maxX},{maxY}&geometryType=esriGeometryEnvelope&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=true&f=geojson
```

**Notes:**

- Max record count = 2000 (use pagination via `resultOffset`/`resultRecordCount`)
- Indicative/high-level location (asset protection/buildover purposes)
- **These are trunk mains, not reticulated sewer** - presence indicates area is likely sewered

**Implemented:** `src/scanner/spatial/melbourne_water.py`

---

### Yarra Valley Water (Reticulated Sewer)

**WFS Endpoint:**

```
https://webmap.yvw.com.au/YVWassets/service.svc/get
```

**Sewer Layers:**

- `SEWERPIPES` - Main sewer pipes (reticulated network)
- `SEWERBRANCHES` - Connections from main to property boundaries
- `SEWERSTRUCTURES` - Maintenance holes, pits, nodes

**⚠️ Limitations:**

- Often times out from some networks (firewall/VPN issues)
- Asset Map URL doesn't support deep-linking with lat/lon params

**Manual Verification:**

1. Open: <https://webmap.yvw.com.au/yvw_ext/>
2. Use search box to find address
3. Check if sewer lines (brown) appear near property

**Alternative:** Call YVW directly: **1300 304 688**

**Implemented:** `src/scanner/spatial/yvw_sewer.py` (with fallback)
