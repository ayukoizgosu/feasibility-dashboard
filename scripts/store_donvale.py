"""Store the Donvale listings from today's browser scrape."""

from datetime import datetime

from scanner.db import get_session, init_db
from scanner.ingest.browser_agent import parse_price
from scanner.models import RawListing, Site

# Initialize DB first
init_db()

# The 21 Donvale listings from browser scrape (2026-01-10)
DONVALE_LISTINGS = [
    {
        "address": "30 Florence Avenue DONVALE",
        "price_text": "$1,249,000",
        "bedrooms": 3,
        "bathrooms": 1,
        "land_size_m2": 726,
        "url": "https://www.domain.com.au/30-florence-avenue-donvale-vic-3111-2020422099",
    },
    {
        "address": "6 Bayles Court DONVALE",
        "price_text": "$1,800,000 - $1,900,000",
        "bedrooms": 5,
        "bathrooms": 3,
        "land_size_m2": 738,
        "url": "https://www.domain.com.au/6-bayles-court-donvale-vic-3111-2020504149",
    },
    {
        "address": "8 Chaim Court DONVALE",
        "price_text": "$1,980,000 - $2,178,000",
        "bedrooms": 4,
        "bathrooms": 2,
        "land_size_m2": 4046,
        "url": "https://www.domain.com.au/8-chaim-court-donvale-vic-3111-2020499362",
    },
    {
        "address": "1 Manna Bank View DONVALE",
        "price_text": "$1,299,000",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 1222,
        "url": "https://www.domain.com.au/1-manna-bank-view-donvale-vic-3111-2020504148",
    },
    {
        "address": "6 MOZART CIRCLE DONVALE",
        "price_text": "$2,000,000 - $2,200,000",
        "bedrooms": 5,
        "bathrooms": 3,
        "land_size_m2": 1500,
        "url": "https://www.domain.com.au/6-mozart-circle-donvale-vic-3111-2020457978",
    },
    {
        "address": "107 Glenvale Road DONVALE",
        "price_text": "$1,190,000-$1,300,000",
        "bedrooms": 3,
        "bathrooms": 2,
        "land_size_m2": 726,
        "url": "https://www.domain.com.au/107-glenvale-road-donvale-vic-3111-2020329735",
    },
    {
        "address": "3 Wellwood Close DONVALE",
        "price_text": "$1.8m - $1.98m",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 4934,
        "url": "https://www.domain.com.au/3-wellwood-close-donvale-vic-3111-2020225190",
    },
    {
        "address": "26 Heads Road DONVALE",
        "price_text": "$1,800,000 - $1,850,000",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 4191,
        "url": "https://www.domain.com.au/26-heads-road-donvale-vic-3111-2019885938",
    },
    {
        "address": "16 Warner Court DONVALE",
        "price_text": "$1,950,000 - $2,145,000",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 4003,
        "url": "https://www.domain.com.au/16-warner-court-donvale-vic-3111-2019829444",
    },
    {
        "address": "2 Quamby Place DONVALE",
        "price_text": "$1.65m - $1.8m",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 4025,
        "url": "https://www.domain.com.au/2-quamby-place-donvale-vic-3111-2019673769",
    },
    {
        "address": "5-7 Rangeview Road DONVALE",
        "price_text": "$1,350,000 - $1,450,000",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 2465,
        "url": "https://www.domain.com.au/5-7-rangeview-road-donvale-vic-3111-2019224773",
    },
    {
        "address": "1 Lookover Road DONVALE",
        "price_text": "$930,000 - $1.02m",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 3997,
        "url": "https://www.domain.com.au/1-lookover-road-donvale-vic-3111-2017994653",
    },
    {
        "address": "2 Utrecht Court DONVALE",
        "price_text": "$1.7m - $1.8m",
        "bedrooms": 4,
        "bathrooms": 2,
        "land_size_m2": 4446,
        "url": "https://www.domain.com.au/2-utrecht-court-donvale-vic-3111-2020501518",
    },
    {
        "address": "319 Oban Road DONVALE",
        "price_text": "$2m - $2.2m",
        "bedrooms": 5,
        "bathrooms": 3,
        "land_size_m2": 5211,
        "url": "https://www.domain.com.au/319-oban-road-donvale-vic-3111-2020404051",
    },
    {
        "address": "26 Florence Avenue DONVALE",
        "price_text": "$1.3m",
        "bedrooms": 3,
        "bathrooms": 1,
        "land_size_m2": 726,
        "url": "https://www.domain.com.au/26-florence-avenue-donvale-vic-3111-2019840393",
    },
    {
        "address": "11 Niagara Road DONVALE",
        "price_text": "$1.1m",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 1919,
        "url": "https://www.domain.com.au/11-niagara-road-donvale-vic-3111-2020011694",
    },
    {
        "address": "1135 Doncaster Road DONVALE",
        "price_text": "$1,650,000 to $1,800,000",
        "bedrooms": None,
        "bathrooms": None,
        "land_size_m2": 650,
        "url": "https://www.domain.com.au/1135-doncaster-road-donvale-vic-3111-2019968964",
    },
    {
        "address": "3/7 Niagara Road DONVALE",
        "price_text": "$950,000 -$1,000,000",
        "bedrooms": 1,
        "bathrooms": 1,
        "land_size_m2": 866,
        "url": "https://www.domain.com.au/3-7-niagara-road-donvale-vic-3111-2018107683",
    },
    {
        "address": "75 Heads Road DONVALE",
        "price_text": "$1,950,000",
        "bedrooms": 5,
        "bathrooms": 4,
        "land_size_m2": None,
        "url": "https://www.domain.com.au/75-heads-road-donvale-vic-3111-2018060755",
    },
    {
        "address": "435 Serpells Terrace DONVALE",
        "price_text": "$1,476,000",
        "bedrooms": 4,
        "bathrooms": 2,
        "land_size_m2": None,
        "url": "https://www.domain.com.au/435-serpells-terrace-donvale-vic-3111-2018303413",
    },
    {
        "address": "57 Glenvale Road DONVALE",
        "price_text": "$963,500",
        "bedrooms": 3,
        "bathrooms": 2,
        "land_size_m2": None,
        "url": "https://www.domain.com.au/57-glenvale-road-donvale-vic-3111-2018350690",
    },
]


def extract_listing_id(url: str) -> str | None:
    """Extract listing ID from Domain URL."""
    import re

    match = re.search(r"-(\d+)$", url)
    return match.group(1) if match else None


def store_donvale_listings():
    """Store all Donvale listings in the database."""
    new_count = 0

    with get_session() as session:
        for listing in DONVALE_LISTINGS:
            listing_id = extract_listing_id(listing["url"])
            if not listing_id:
                print(f"  Skipping (no ID): {listing['address']}")
                continue

            raw_id = f"domain_browser:{listing_id}"

            # Check if exists
            existing = session.query(RawListing).filter_by(id=raw_id).first()
            if existing:
                print(f"  Already exists: {listing['address']}")
                continue

            # Create raw listing
            raw = RawListing(
                id=raw_id,
                source="domain_browser",
                listing_id=listing_id,
                url=listing["url"],
                payload=listing,
            )
            session.add(raw)

            # Parse price
            price_low, price_high, price_guide = parse_price(
                listing.get("price_text", "")
            )

            # Create site
            site = Site(
                source="domain_browser",
                domain_listing_id=listing_id,
                url=listing["url"],
                address_raw=listing["address"],
                suburb="Donvale",
                postcode="3111",
                state="VIC",
                property_type="house" if listing.get("bedrooms") else "vacant_land",
                price_display=listing.get("price_text"),
                price_low=price_low,
                price_high=price_high,
                price_guide=price_guide,
                bedrooms=listing.get("bedrooms"),
                bathrooms=listing.get("bathrooms"),
                land_size_listed=listing.get("land_size_m2"),
                geocode_status="pending",
            )
            session.add(site)
            new_count += 1
            print(f"  Added: {listing['address']} - {listing['price_text']}")

    print(f"\nStored {new_count} new listings")
    return new_count


if __name__ == "__main__":
    store_donvale_listings()
    store_donvale_listings()
