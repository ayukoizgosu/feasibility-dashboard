# Feasibility Dashboard

Automated pipeline to identify sub-$2M subdivision opportunities in Melbourne.

## Quick Start

```bash
# Install dependencies
make setup

# Download Victorian spatial data (one-time)
# See "Data Setup" section below

# Run full pipeline
make run
```

## Commands

| Command | Description |
|---------|-------------|
| `make setup` | Install dependencies + Playwright |
| `make scrape` | Scrape Domain + REA listings |
| `make geocode` | Geocode pending listings |
| `make load-spatial` | Load Victorian cadastre + planning data |
| `make evaluate` | Evaluate planning constraints |
| `make score` | Calculate feasibility scores |
| `make report` | Export top 25 sites |
| `make run` | Full pipeline end-to-end |

## Data Setup

Download these files from data.vic.gov.au and save to `data/`:

1. **Cadastre** (parcels): [Vicmap Property Simplified](https://discover.data.vic.gov.au/dataset/vicmap-property-simplified-1-parcel-view)
   - Save as: `data/vicmap_property.gpkg`

2. **Planning Zones**: [Planning Scheme Zones](https://discover.data.vic.gov.au/dataset/planning-scheme-zones)
   - Save as: `data/planning_zones.gpkg`

3. **Planning Overlays**: [Planning Scheme Overlays](https://discover.data.vic.gov.au/dataset/planning-scheme-overlays)
   - Save as: `data/planning_overlays.gpkg`

Then run:

```bash
make load-spatial
```

## Configuration

Edit `config.yaml` to customize:

- Target suburbs
- Price/land size filters
- Feasibility assumptions
- Constraint severity mappings

## Output

Reports are generated in `reports/`:

- `top_sites.csv` - Summary of top 25 opportunities
- `site_<id>.md` - Detailed Markdown report per site
- `site_<id>.json` - Machine-readable data per site

## Architecture

```
src/scanner/
├── ingest/      # Domain + REA scrapers
├── geocode/     # Nominatim geocoder (free)
├── spatial/     # Victorian data loading
├── constraints/ # Planning constraint evaluation
├── feasibility/ # Yield + profit scoring
└── reporting/   # CSV + MD export
```
