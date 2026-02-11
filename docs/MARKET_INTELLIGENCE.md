# Market Intelligence Module

## Overview

The Market Intelligence module provides data-backed property valuations for the site-scanner tool. It uses scraped comparable sales data to estimate:

1. **End Value** - What a developed property could sell for
2. **Land Value** - The implied land component using residual valuation
3. **Construction Cost** - Estimated build costs by quality tier

## Key Features

### Property Classification

Properties are classified by:
- **Type**: House, Townhouse, Unit, Acreage, Vacant Land
- **Quality**: Basic, Standard, Premium, Luxury
- **Era/Age**: Pre-1920 to Post-2010
- **Renovation Status**: Renovated, Unrenovated, Unknown

### GRV Analysis

Full Gross Realisation Value analysis including:
- Adjusted comparable pricing (accounts for land size, type, quality differences)
- Residual land value calculation
- Construction cost estimation with breakdowns
- Feasibility summary with margin percentage

### Dual-Occupancy Analysis

Dedicated analysis for dual-occ development:
- Calculates end value per townhouse unit
- Uses townhouse comparables (falls back to adjusted house values)
- Accurate construction costs for 2x dwellings
- Higher viability threshold (18% vs 15%) due to complexity

## CLI Usage

### Basic Scan
```bash
python -m scanner.scan_single "123 Example Street, Doncaster East"
```

### With Quality Tier
```bash
python -m scanner.scan_single "123 Example Street, Doncaster East" --quality Premium
```

### Dual-Occupancy Analysis
```bash
python -m scanner.scan_single "123 Example Street, Doncaster East" --dual-occ
```

### Combined
```bash
python -m scanner.scan_single "123 Example Street, Doncaster East" --dual-occ --quality Premium
```

## Data Sources

### Scraped Data
- **Domain.com.au**: Sold listings with price, land size, bedrooms, etc.
- **Realestate.com.au (REA)**: Secondary source, more aggressive bot protection

### Cached Data
- **market_data.db**: SQLite database of comparable sales
- **sites.db**: Contains transmission line cache (3,030+ lines)

## Construction Cost Benchmarks

| Quality | Rate ($/sqm) | Description |
|---------|--------------|-------------|
| Basic | $2,000 | Budget/knockdown rebuild |
| Standard | $2,800 | Standard project home |
| Premium | $3,800 | Quality build with upgrades |
| Luxury | $5,500 | Architect-designed, high-end |

## Viability Thresholds

| Development Type | Min Margin | Rationale |
|-----------------|------------|-----------|
| Single Dwelling | 15% | Standard development risk |
| Dual-Occ | 18% | Higher complexity, more risk |
| Subdivision | 15% | Lower build risk |

## Files

| File | Purpose |
|------|---------|
| `src/scanner/market/intel.py` | Main intelligence module |
| `src/scanner/market/classifiers.py` | Property classification utilities |
| `src/scanner/market/models.py` | Database models (Comparable) |
| `src/scanner/market/database.py` | Database operations |
| `market_data.db` | Comparable sales database |

## Scraping

### Harvest Market Data
```bash
python scripts/harvest_intel_vpn.py
```
This script:
- Rotates VPN connections (ExpressVPN required)
- Alternates between Domain and REA
- Scrapes sold listings for target suburbs
- Saves to market_data.db

### Verify Database Contents
```bash
python scripts/verify_db.py
```

## API Functions

### `get_grv_analysis()`
Complete single-dwelling GRV analysis.

### `get_dual_occ_grv_analysis()`
Dual-occupancy specific analysis.

### `estimate_purchase_price()`
Simple purchase price estimation (backwards compatible).

### `estimate_construction_cost()`
Construction cost calculation by quality tier.
