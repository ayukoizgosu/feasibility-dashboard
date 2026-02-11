"""Domain.com.au scraper with human-like behavior."""

import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import Stealth
from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.ingest.human_like import (
    SessionManager,
    human_scroll,
    random_delay,
    setup_human_browser,
    simulate_reading,
)
from scanner.market.database import save_comparable
from scanner.market.models import SessionLocal as MarketSessionLocal
from scanner.models import RawListing, Site
from scanner.utils.delegator import delegate_extraction

console = Console()


class DomainScraper:
    """Human-like scraper for Domain.com.au."""

    BASE_URL = "https://www.domain.com.au"

    def __init__(self):
        self.config = get_config()
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.session = SessionManager(max_pages_per_session=30)

    async def start(self):
        """Start browser with human-like settings."""
        playwright = await async_playwright().start()

        # Use headed browser occasionally for more realistic behavior
        headless = random.random() > 0.1  # 90% headless, 10% headed

        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-AU",
            timezone_id="Australia/Melbourne",
        )

        # Block unnecessary resources to speed up
        # await self.context.route(
        #     "**/*.{png,jpg,jpeg,gif,svg,ico}", lambda route: route.abort()
        # )
        # await self.context.route("**/analytics**", lambda route: route.abort())
        # await self.context.route("**/tracking**", lambda route: route.abort())

        self.page = await self.context.new_page()
        await Stealth().apply_stealth_async(self.page)
        await setup_human_browser(self.page)

        # Visit homepage first like a real user
        console.print("[dim]Visiting homepage first...[/dim]")
        await self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
        await simulate_reading(self.page, 2, 5)

    async def stop(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    def build_search_url(
        self,
        suburb: str,
        page: int = 1,
        search_type: str = "sale",
        property_types: list[str] | None = None,
        price_max: int | None = None,
        land_size_min: int | None = None,
    ) -> str:
        """Construct domain.com.au search URL."""
        # Normalize property types
        raw_types = property_types or self.config.filters.property_types
        ptypes = []
        for pt in raw_types:
            pt_low = pt.lower()
            if "house" == pt_low:
                ptypes.append("house")
            elif "vacant_land" == pt_low or "land" in pt_low:
                ptypes.append("vacant-land")
            elif "townhouse" == pt_low or "town-house" == pt_low:
                ptypes.append("town-house")
            elif "unit" in pt_low or "apartment" in pt_low:
                ptypes.append("apartment-unit-flat")

        if not ptypes:
            ptypes = ["house", "town-house"]
        # Use %2C for commas to be safe (url encoding)
        ptype_str = "%2C".join(ptypes)

        # Suburb to postcode mapping for better URL generation
        SUBURB_POSTCODES = {
            "doncaster": "3108",
            "doncaster east": "3109",
            "donvale": "3111",
            "templestowe": "3106",
            "templestowe lower": "3107",
            "bulleen": "3105",
            "park orchards": "3114",
            "warrandyte": "3113",
            "wonga park": "3115",
        }

        # Extract postcode if present (e.g. "Doncaster 3108")
        postcode = ""
        suburb_clean = suburb.lower().strip()

        # Check if postcode is already in the string
        match = re.search(r"(\d{4})$", suburb_clean)
        if match:
            postcode = match.group(1)
            suburb_clean = suburb_clean.replace(postcode, "").strip()

        # If no postcode found in string, try mapping
        if not postcode:
            postcode = SUBURB_POSTCODES.get(suburb_clean, "")

        suburb_slug = suburb_clean.replace(" ", "-")

        # Overrides
        p_max = price_max if price_max is not None else self.config.filters.price_max
        l_min = (
            land_size_min
            if land_size_min is not None
            else self.config.filters.land_size_min_m2
        )

        if search_type == "sold":
            # https://www.domain.com.au/sold-listings/doncaster-vic-3108/
            url_slug = (
                f"{suburb_slug}-vic-{postcode}" if postcode else f"{suburb_slug}-vic"
            )
            url = f"{self.BASE_URL}/sold-listings/{url_slug}/"
            url += f"?ptype={ptype_str}"
            url += "&excludepricewithheld=1"
        else:
            # Sale often works without postcode, but including it is safer if we have it
            url_slug = (
                f"{suburb_slug}-vic-{postcode}" if postcode else f"{suburb_slug}-vic"
            )
            url = f"{self.BASE_URL}/sale/{url_slug}/"
            url += f"?ptype={ptype_str}"
            url += f"&price=0-{p_max}"
            url += f"&landsize={l_min}-any"
            url += "&excludeunderoffer=1"

        if page > 1:
            url += f"&page={page}"

        return url

    async def scrape_suburb(
        self,
        suburb: str,
        property_types: list[str] = None,
        max_pages: int = 5,
        search_type: str = "sale",
        price_max: int | None = None,
        land_size_min: int | None = None,
    ) -> list[dict[str, Any]]:
        """Scrape listings for a suburb with human-like behavior."""
        listings = []
        page_num = 1

        label = "SOLD" if search_type == "sold" else "SALE"
        console.print(f"[blue]Scraping Domain ({label}): {suburb}[/blue]")

        while page_num <= max_pages:
            # Check if we need a break
            if self.session.should_take_break():
                console.print("[dim]Taking a short break...[/dim]")
                await self.session.take_break()

            url = self.build_search_url(
                suburb,
                page_num,
                search_type=search_type,
                price_max=price_max,
                land_size_min=land_size_min,
                property_types=property_types,
            )
            console.print(f"[dim]DEBUG URL: {url}[/dim]")

            try:
                # Random delay before navigating
                await random_delay(2, 5)

                # Navigate
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Simulate human viewing the page
                await simulate_reading(self.page, 3, 7)

                # Scroll down to load more content
                for _ in range(random.randint(2, 4)):
                    await human_scroll(self.page)
                    await random_delay(0.5, 1.5)

                # Check for no results
                content = await self.page.content()
                if (
                    "no properties" in content.lower()
                    or "0 properties" in content.lower()
                ):
                    break

                # Extract listings
                # Extract listings
                # Extract listings - try multiple patterns
                all_cards = await self.page.query_selector_all(
                    '[data-testid^="listing-card-wrapper"], [data-testid^="listing-card-"], [data-testid="results"] li[data-testid^="listing-"]'
                )

                # Filter to unique IDs to avoid 3x duplicates
                cards = []
                seen_card_ids = set()
                for card in all_cards:
                    tid = await card.get_attribute("data-testid")
                    if tid and tid not in seen_card_ids:
                        seen_card_ids.add(tid)
                        cards.append(card)

                if not cards:
                    # Final fallback to standard result classes
                    cards = await self.page.query_selector_all(
                        '[class*="listing-result"]'
                    )

                if not cards:
                    console.print(
                        f"  [yellow]No cards found on page {page_num}[/yellow]"
                    )
                    try:
                        # Debug: dumps ids found
                        content = await self.page.content()
                        ids = re.findall(r'data-testid="([^"]+)"', content)
                        console.print(
                            f"  [dim]Debug: Found {len(ids)} testids on page. Sample: {ids[:5]}[/dim]"
                        )
                    except Exception:
                        pass
                    break

                for card in cards:
                    try:
                        listing = await self._extract_listing(card, suburb)
                        if listing:
                            listings.append(listing)
                    except Exception:
                        pass  # Silent fail on individual cards

                console.print(f"  Page {page_num}: {len(cards)} listings")

                # Check for next page
                if page_num < max_pages:
                    next_exists = await self.page.query_selector(
                        '[data-testid="paginator-next-page"]:not([disabled])'
                    )
                    if not next_exists:
                        break

                page_num += 1

                # Random delay between pages (longer than normal)
                await random_delay(3, 8)

            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
                await random_delay(5, 10)  # Longer delay after error
                break

        console.print(f"  Total for {suburb}: {len(listings)}")
        return listings

    async def _extract_listing(self, card, suburb: str) -> dict[str, Any] | None:
        """Extract data from a listing card."""
        try:
            # Get link - Domain sold URLs can be address-based or property-based
            # e.g. /21-tracey-street-doncaster-east-vic-3109-2012345678
            link = await card.query_selector("a[href*='/property-'], a[href*='vic-']")
            if not link:
                link = await card.query_selector("a")

            if not link:
                # Many <li> in the results might be layout spacers or ads
                return None

            href = await link.get_attribute("href")
            if not href:
                if "sold" in suburb.lower() or "sold" in self.page.url:
                    console.print("  [red]Debug: Missing href in link[/red]")
                return None

            if not href.startswith("http"):
                href = f"{self.BASE_URL}{href}"

            # Log found link for debug
            console.print(f"  [dim]Found link: {href}[/dim]")

            # Extract ID (robust)
            # URL can be /123 or /address-slug-123
            # We look for the last sequence of digits in the path
            url_path = href.split("?")[0]
            ids = re.findall(r"(\d+)", url_path)
            listing_id = ids[-1] if ids else None

            if not listing_id:
                if "sold" in suburb.lower() or "sold" in self.page.url:
                    console.print(f"  [red]Debug: No ID found in href: {href}[/red]")
                return None

            # Get text content for parsing
            text = await card.inner_text()

            # Try specific selector for address first
            address = ""
            h2 = await card.query_selector("h2")
            if h2:
                address = await h2.inner_text()

            # Parse lines
            lines = [
                line_text.strip() for line_text in text.split("\n") if line_text.strip()
            ]

            if not address and lines:
                # Fallback, but skip status tags or lines that look like prices
                for line in lines:
                    if any(k in line.lower() for k in ["new", "sold", "offer"]):
                        continue
                    if "$" in line:  # Skip prices
                        continue
                    if re.match(r".*\d+.*", line):  # Has number
                        address = line
                        break
                if not address:
                    # Final resort: if line[0] is not a price, take it
                    if lines and "$" not in lines[0]:
                        address = lines[0]

            # Parse price and sold info
            price_text = ""
            sold_date = None
            agency = ""
            agent = ""

            for i, line in enumerate(lines):
                line_low = line.lower()

                # Check for Sold Status and Date
                if "sold" in line_low:
                    # Look for date in this line
                    date_match = re.search(r"(\d{1,2}\s+[a-zA-Z]{3}\s+\d{4})", line)
                    if date_match:
                        try:
                            sold_date = datetime.strptime(
                                date_match.group(1), "%d %b %Y"
                            ).isoformat()
                        except Exception:
                            pass

                    # If this is the 'Sold' line, the next 1-2 lines might be agent/agency
                    # (But skip if they are empty or look like prices)
                    potential_idx = i + 1
                    while potential_idx < len(lines) and potential_idx <= i + 3:
                        p_line = lines[potential_idx]
                        if not p_line.strip():
                            potential_idx += 1
                            continue
                        if (
                            "$" in p_line
                            or "beds" in p_line.lower()
                            or "price" in p_line.lower()
                        ):
                            break
                        if not agent:
                            agent = p_line
                        elif not agency:
                            agency = p_line
                            break
                        potential_idx += 1

                # Look for price
                if "$" in line and not price_text:
                    if "m²" not in line:  # Avoid land size
                        price_text = line

            if not price_text:
                for line in lines:
                    if "price withheld" in line.lower():
                        price_text = "Price Withheld"
                        break

            # Parse features
            beds = baths = cars = None
            if lines:  # Assuming 'details' should be 'lines' based on context
                for detail_line in lines:  # Renamed 'line' to 'detail_line'
                    # Be more robust
                    if "bed" in detail_line.lower():
                        match = re.search(r"(\d+)", detail_line)
                        beds = int(match.group(1)) if match else None
                    if "bath" in detail_line.lower():
                        match = re.search(r"(\d+)", detail_line)
                        baths = int(match.group(1)) if match else None
                    if "car" in detail_line.lower():  # e.g. "2 Parking" or "2 Car"
                        match = re.search(r"(\d+)", detail_line)
                        cars = int(match.group(1)) if match else None

            # Parse land size
            land_size = None
            land_match = re.search(r"(\d{3,})\s*m[²2]", text)
            if land_match:
                land_size = float(land_match.group(1))

            # Extract Days on Market
            days_on_market = None
            dom_match = re.search(
                r"(\d+)\s*days\s*on\s*market|sold\s*in\s*(\d+)\s*days", text.lower()
            )
            if dom_match:
                days_on_market = int(dom_match.group(1) or dom_match.group(2))

            # Infer Property Type
            property_type = "House"
            if any(k in text.lower() for k in ["townhouse", "town house"]):
                property_type = "Townhouse"
            elif any(k in text.lower() for k in ["unit", "apartment", "flat", "villa"]):
                property_type = "Unit"
            elif "vacant land" in text.lower():
                property_type = "Land"

            # Extract Agency
            # Extract Agency - Improved Selector
            agency = None
            try:
                # Try logo image alt
                branding_img = await card.query_selector(
                    "img[alt*='Agency'], img[class*='logo']"
                )
                if branding_img:
                    alt = await branding_img.get_attribute("alt")
                    if alt and len(alt) > 2:
                        agency = alt.replace("Logo", "").replace("logo", "").strip()

                # Try text fallback
                if not agency:
                    branding_text = await card.query_selector(
                        "span[data-testid='agency-name'], span[class*='branding']"
                    )
                    if branding_text:
                        agency = (await branding_text.text_content()).strip()
            except Exception:
                pass

            # Feature Extraction via Antigravity Delegator (Gemini)
            # We delegate the complex reading to Gemini CLI
            rich_features = delegate_extraction(text)

            # Merge rich features or fallback to regex
            finish_quality = rich_features.get("finish_quality", "Standard")
            building_area = rich_features.get("internal_area_m2")
            renovated = rich_features.get("renovated", False)
            p_type_rich = rich_features.get("property_type")
            if p_type_rich and p_type_rich in [
                "House",
                "Townhouse",
                "Unit",
                "Apartment",
                "Land",
            ]:
                property_type = p_type_rich

            # The original `features_text` was used for regex fallback, so keep it.
            features_text = text.lower()
            if not building_area:
                # Regex Fallback for area
                sq_match = re.search(r"(\d{2,})\s*sq(?:uares)?\b", features_text)
                if sq_match:
                    building_area = float(sq_match.group(1)) * 9.29
                else:
                    sqm_match = re.search(r"(\d{3,})\s*sqm\b", features_text)
                    if sqm_match:
                        building_area = float(sqm_match.group(1))

            return {
                "listing_id": listing_id,
                "url": href,
                "address": address,
                "suburb": suburb,
                "price_text": price_text,
                "bedrooms": beds,
                "bathrooms": baths,
                "car_spaces": cars,
                "land_size_m2": land_size,
                "property_type": property_type,
                "renovated": renovated,
                "features": rich_features.get("features", []),
                "agency": agency,
                "agent": agent,
                # Store full text plus derived features
                "building_area": building_area,
                "finish_quality": finish_quality,
                "year_built": rich_features.get("year_built_estimate"),
                "description_snippet": features_text[:500],
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "sold_date": sold_date,
                "days_on_market": days_on_market,
            }

        except Exception as e:
            # Debug why it failed
            if "sold" in suburb.lower() or "sold" in self.page.url:
                console.print(f"  [red]Failed to extract card: {e}[/red]")
            return None

    def parse_price(
        self, price_text: str
    ) -> tuple[float | None, float | None, float | None]:
        """Parse price text."""
        if not price_text:
            return None, None, None

        price_text = price_text.lower().replace(",", "").replace("$", "")

        # Range
        range_match = re.search(r"([\d.]+)\s*m?\s*[-–to]+\s*([\d.]+)\s*m?", price_text)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            if low < 100:
                low *= 1_000_000
            if high < 100:
                high *= 1_000_000
            return low, high, (low + high) / 2

        # Single with m
        single_match = re.search(r"([\d.]+)\s*m", price_text)
        if single_match:
            value = float(single_match.group(1)) * 1_000_000
            return value, value, value

        # Plain number
        num_match = re.search(r"(\d{6,})", price_text)
        if num_match:
            value = float(num_match.group(1))
            return value, value, value

        return None, None, None


async def scrape_domain(suburbs: list[str] | None = None) -> int:
    """Scrape Domain with human-like behavior."""
    config = get_config()
    suburbs = suburbs or config.suburbs

    if not suburbs:
        console.print("[yellow]No suburbs configured[/yellow]")
        return 0

    # Limit to a few suburbs per run to stay under radar
    max_suburbs_per_run = 4
    if len(suburbs) > max_suburbs_per_run:
        console.print(f"[dim]Limiting to {max_suburbs_per_run} suburbs this run[/dim]")
        suburbs = random.sample(suburbs, max_suburbs_per_run)

    scraper = DomainScraper()

    try:
        await scraper.start()

        total_new = 0

        for suburb in suburbs:
            listings = await scraper.scrape_suburb(suburb, max_pages=3)

            with get_session() as session:
                for listing in listings:
                    # Skip excluded
                    if any(
                        kw in listing.get("address", "").lower()
                        for kw in config.filters.exclude_keywords
                    ):
                        continue

                    listing_id = listing["listing_id"]
                    raw_id = f"domain:{listing_id}"

                    existing = session.query(RawListing).filter_by(id=raw_id).first()
                    if existing:
                        existing.fetched_at = datetime.utcnow()
                        existing.payload = listing
                        continue

                    raw = RawListing(
                        id=raw_id,
                        source="domain",
                        listing_id=listing_id,
                        url=listing["url"],
                        payload=listing,
                    )
                    session.add(raw)

                    site = (
                        session.query(Site)
                        .filter_by(domain_listing_id=listing_id)
                        .first()
                    )
                    if not site:
                        price_low, price_high, price_guide = scraper.parse_price(
                            listing.get("price_text", "")
                        )

                        site = Site(
                            source="domain",
                            domain_listing_id=listing_id,
                            url=listing["url"],
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
                        total_new += 1
                    else:
                        site.last_seen = datetime.utcnow()

            # Longer break between suburbs
            await random_delay(10, 20)

        console.print(f"[green]Domain: {total_new} new listings[/green]")
        return total_new

    finally:
        await scraper.stop()


async def scrape_sold_domain(suburbs: list[str] | None = None, max_pages: int = 3):
    """Scrape SOLD listings from Domain to populate market data."""
    config = get_config()
    suburbs = suburbs or config.suburbs

    if not suburbs:
        console.print("[yellow]No suburbs configured for sold scrape[/yellow]")
        return 0

    scraper = DomainScraper()
    try:
        await scraper.start()
        total_saved = 0

        for suburb in suburbs:
            # Scrape sold listings
            listings = await scraper.scrape_suburb(
                suburb, max_pages=max_pages, search_type="sold"
            )

            from scanner.market.models import get_db

            # Use next() because it's a generator
            db_gen = get_db()
            db = next(db_gen)

            try:
                for listing in listings:
                    # Enrich with suburb if missing from extracted address
                    if not listing.get("suburb"):
                        listing["suburb"] = suburb

                    save_comparable(db, listing)
                    total_saved += 1
            finally:
                db.close()

            await random_delay(15, 30)

        console.print(
            f"[green]Done! Saved {total_saved} sold listings to market database.[/green]"
        )
        return total_saved
    finally:
        await scraper.stop()


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--suburb", type=str, help="Specific suburb to scrape")
    parser.add_argument(
        "--type", type=str, choices=["sale", "sold"], default="sale", help="Search type"
    )
    parser.add_argument("--limit", type=int, default=3, help="Max pages to scrape")
    args = parser.parse_args()

    suburbs = [args.suburb] if args.suburb else None

    if args.type == "sold":
        asyncio.run(scrape_sold_domain(suburbs, max_pages=args.limit))
    else:
        asyncio.run(scrape_domain(suburbs))


if __name__ == "__main__":
    run()
