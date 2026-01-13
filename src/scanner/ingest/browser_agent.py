"""Browser agent scraper using Antigravity's browser subagent.

This module provides human-like scraping by leveraging Antigravity's browser
which operates as a real browser with natural fingerprints, avoiding detection.

IMPORTANT: This module is designed to be called by Antigravity agents, not
directly by Python code. The scraping happens through browser_subagent tool calls.
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path  # noqa: F401 - used by external callers
from typing import Any

from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.models import RawListing, Site

console = Console()


class BrowserAgentConfig:
    """Conservative configuration for browser-based scraping."""

    # Very conservative to avoid detection
    MAX_PAGES_PER_SESSION = 3
    MAX_SUBURBS_PER_RUN = 2
    MIN_DWELL_SECONDS = 8
    MAX_DWELL_SECONDS = 25
    MIN_BREAK_BETWEEN_SUBURBS_SECONDS = 60
    MAX_BREAK_BETWEEN_SUBURBS_SECONDS = 180

    # Patterns to avoid (honeypots, traps)
    AVOID_LINK_PATTERNS = [
        r"subscribe",
        r"newsletter",
        r"saved-search",
        r"alert",
        r"sign-in",
        r"login",
        r"register",
        r"email",
    ]


def build_domain_search_url(suburb: str, page: int = 1) -> str:
    """Build Domain.com.au search URL for a suburb."""
    config = get_config()

    property_types = []
    for pt in config.filters.property_types:
        if pt == "house":
            property_types.append("house")
        elif pt == "vacant_land":
            property_types.append("vacant-land")

    ptype_str = ",".join(property_types) if property_types else "house"
    suburb_slug = suburb.lower().replace(" ", "-")

    url = f"https://www.domain.com.au/sale/{suburb_slug}-vic/"
    url += f"?ptype={ptype_str}"
    url += f"&price=0-{config.filters.price_max}"
    url += f"&landsize={config.filters.land_size_min_m2}-any"
    url += "&excludeunderoffer=1"

    if page > 1:
        url += f"&page={page}"

    return url


def generate_browser_task_prompt(suburb: str, source: str = "domain") -> str:
    """Generate a detailed prompt for the browser subagent to scrape listings.

    This prompt instructs the browser agent to:
    1. Navigate to the search page
    2. Behave like a human (scroll, pause, move mouse)
    3. Extract listing information from the visible cards
    4. Return structured data
    """
    _ = get_config()  # Load config to validate it exists
    url = build_domain_search_url(suburb)

    dwell_time = random.randint(
        BrowserAgentConfig.MIN_DWELL_SECONDS, BrowserAgentConfig.MAX_DWELL_SECONDS
    )

    prompt = f"""Navigate to Domain.com.au and extract property listings for {suburb}, VIC.

**URL**: {url}

**CRITICAL INSTRUCTIONS - Act Like a Human**:
1. After the page loads, wait {dwell_time} seconds while naturally viewing the page
2. Scroll down slowly in 2-3 increments (not all at once)
3. Move your mouse around occasionally - don't leave it static
4. DO NOT click any links that contain: subscribe, newsletter, alert, sign-in, login, saved-search

**Data to Extract**:
For each property listing card visible on the page, extract:
- Address (full street address)
- Price text (as displayed, e.g. "$1,200,000" or "Contact Agent")
- Number of bedrooms (if shown)
- Number of bathrooms (if shown)
- Land size in m² (if shown)
- Listing URL (the href to the property detail page)

**Return Format**:
Return a JSON array of listings. Example:
```json
[
  {{
    "address": "123 Smith Street, {suburb} VIC",
    "price_text": "$1,200,000",
    "bedrooms": 3,
    "bathrooms": 2,
    "land_size_m2": 650,
    "url": "https://www.domain.com.au/123-smith-street-..."
  }}
]
```

If there are NO listings or the page shows an error/captcha, return:
```json
{{"error": "description of what you saw"}}
```

**STOP CONDITION**: Return once you have extracted all VISIBLE listing cards on the first page. Do not navigate to page 2.
"""
    return prompt


def parse_browser_agent_response(
    response_text: str, suburb: str
) -> list[dict[str, Any]]:
    """Parse the browser agent's response into listing dictionaries.

    Args:
        response_text: Raw text response from browser agent
        suburb: The suburb being scraped (for context)

    Returns:
        List of parsed listing dictionaries
    """
    # Try to extract JSON from the response
    json_match = re.search(r"\[[\s\S]*\]", response_text)
    if not json_match:
        # Check for error response
        error_match = re.search(r'\{[\s\S]*"error"[\s\S]*\}', response_text)
        if error_match:
            try:
                error_data = json.loads(error_match.group())
                console.print(
                    f"[yellow]Browser agent error: {error_data.get('error')}[/yellow]"
                )
            except json.JSONDecodeError:
                console.print(
                    f"[yellow]Could not parse browser agent response[/yellow]"
                )
        return []

    try:
        listings = json.loads(json_match.group())
        if not isinstance(listings, list):
            return []

        # Normalize and validate listings
        valid_listings = []
        for listing in listings:
            if not isinstance(listing, dict):
                continue
            if not listing.get("address") and not listing.get("url"):
                continue

            # Extract listing ID from URL
            listing_id = None
            url = listing.get("url", "")
            id_match = re.search(r"/(\d+)(?:\?|$)", url)
            if id_match:
                listing_id = id_match.group(1)

            normalized = {
                "listing_id": listing_id,
                "url": url,
                "address": listing.get("address", ""),
                "suburb": suburb,
                "price_text": listing.get("price_text", ""),
                "bedrooms": listing.get("bedrooms"),
                "bathrooms": listing.get("bathrooms"),
                "car_spaces": listing.get("car_spaces"),
                "land_size_m2": listing.get("land_size_m2"),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "domain_browser",
            }
            valid_listings.append(normalized)

        return valid_listings

    except json.JSONDecodeError:
        console.print("[red]Failed to parse JSON from browser response[/red]")
        return []


def parse_price(price_text: str) -> tuple[float | None, float | None, float | None]:
    """Parse price text into low, high, and guide values."""
    if not price_text:
        return None, None, None

    price_text = price_text.lower().replace(",", "").replace("$", "")

    # Range (e.g., "1.2m - 1.4m")
    range_match = re.search(r"([\d.]+)\s*m?\s*[-–to]+\s*([\d.]+)\s*m?", price_text)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        if low < 100:
            low *= 1_000_000
        if high < 100:
            high *= 1_000_000
        return low, high, (low + high) / 2

    # Single with 'm' (e.g., "1.2m")
    single_match = re.search(r"([\d.]+)\s*m", price_text)
    if single_match:
        value = float(single_match.group(1)) * 1_000_000
        return value, value, value

    # Plain number (e.g., "1200000")
    num_match = re.search(r"(\d{6,})", price_text)
    if num_match:
        value = float(num_match.group(1))
        return value, value, value

    return None, None, None


def store_listings(listings: list[dict[str, Any]]) -> int:
    """Store parsed listings in the database.

    Args:
        listings: List of listing dictionaries from browser agent

    Returns:
        Number of new listings stored
    """
    config = get_config()
    new_count = 0

    with get_session() as session:
        for listing in listings:
            # Skip if no ID
            listing_id = listing.get("listing_id")
            if not listing_id:
                continue

            # Skip excluded keywords
            address = listing.get("address", "").lower()
            if any(kw in address for kw in config.filters.exclude_keywords):
                continue

            raw_id = f"domain_browser:{listing_id}"

            # Check if exists
            existing = session.query(RawListing).filter_by(id=raw_id).first()
            if existing:
                existing.fetched_at = datetime.utcnow()
                existing.payload = listing
                continue

            # Create raw listing
            raw = RawListing(
                id=raw_id,
                source="domain_browser",
                listing_id=listing_id,
                url=listing.get("url"),
                payload=listing,
            )
            session.add(raw)

            # Create or update site
            site = session.query(Site).filter_by(domain_listing_id=listing_id).first()
            if not site:
                price_low, price_high, price_guide = parse_price(
                    listing.get("price_text", "")
                )

                site = Site(
                    source="domain_browser",
                    domain_listing_id=listing_id,
                    url=listing.get("url"),
                    address_raw=listing.get("address"),
                    suburb=listing.get("suburb"),
                    state="VIC",
                    property_type="house",
                    price_display=listing.get("price_text"),
                    price_low=price_low,
                    price_high=price_high,
                    price_guide=price_guide,
                    bedrooms=listing.get("bedrooms"),
                    bathrooms=listing.get("bathrooms"),
                    car_spaces=listing.get("car_spaces"),
                    land_size_listed=listing.get("land_size_m2"),
                    geocode_status="pending",
                )
                session.add(site)
                new_count += 1
            else:
                site.last_seen = datetime.utcnow()

    return new_count


def get_random_suburbs(count: int = None) -> list[str]:
    """Get a random selection of suburbs for this run.

    Args:
        count: Number of suburbs to return (default: MAX_SUBURBS_PER_RUN)

    Returns:
        Shuffled list of suburbs
    """
    config = get_config()
    suburbs = list(config.suburbs)

    if count is None:
        count = BrowserAgentConfig.MAX_SUBURBS_PER_RUN

    if len(suburbs) > count:
        suburbs = random.sample(suburbs, count)
    else:
        random.shuffle(suburbs)

    return suburbs


# Export key functions for use by agents
__all__ = [
    "BrowserAgentConfig",
    "build_domain_search_url",
    "generate_browser_task_prompt",
    "parse_browser_agent_response",
    "store_listings",
    "get_random_suburbs",
]
