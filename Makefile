.PHONY: setup install scrape geocode load-spatial evaluate score report run clean

# Initial setup
setup:
	poetry install
	poetry run playwright install chromium
	mkdir -p data db reports

# Install dependencies only
install:
	poetry install

# Scrape listings from Domain + REA
scrape:
	poetry run python -m scanner.ingest.run

# Geocode new listings
geocode:
	poetry run python -m scanner.geocode.run

# Load Victorian spatial data
load-spatial:
	poetry run python -m scanner.spatial.load

# Evaluate constraints
evaluate:
	poetry run python -m scanner.constraints.run

# Calculate feasibility scores
score:
	poetry run python -m scanner.feasibility.run

# Export reports
report:
	poetry run python -m scanner.reporting.run

# Full pipeline
run:
	poetry run python scripts/run_pipeline.py

# Clean generated files
clean:
	rm -rf db/*.db reports/*.csv reports/*.md reports/*.json

# Weekly LDRZ refresh
weekly-refresh:
	poetry run python scripts/weekly_refresh_ldrz.py --suburbs-file config/suburbs_metro_east.txt
