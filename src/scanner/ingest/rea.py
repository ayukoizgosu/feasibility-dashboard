"""realestate.com.au scraper with human-like behavior.

WARNING: REA uses Kasada bot protection which is aggressive.
This scraper includes extensive evasion techniques but may still get blocked.
Consider using Domain as primary source.
"""

import asyncio
import random
import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from rich.console import Console

from scanner.config import get_config
from scanner.db import get_session
from scanner.ingest.human_like import (
    SessionManager,
    human_move_mouse,
    human_scroll,
    random_delay,
    setup_human_browser,
    simulate_reading,
)
from scanner.market.database import save_comparable
from scanner.market.utils import parse_sold_price
from scanner.models import RawListing, Site

console = Console()


class REAScraper:
    """Human-like scraper for realestate.com.au."""

    BASE_URL = "https://www.realestate.com.au"

    def __init__(self):
        self.config = get_config()
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.session = SessionManager(
            max_pages_per_session=20
        )  # More conservative for REA

    async def start(self):
        """Start browser with stealth settings."""
        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        # Realistic context
        self.context = await self.browser.new_context(
            viewport={"width": 1536, "height": 864},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-AU",
            timezone_id="Australia/Melbourne",
            geolocation={"latitude": -37.8136, "longitude": 144.9631},  # Melbourne
            permissions=["geolocation"],
        )

        # Block trackers
        await self.context.route("**/analytics**", lambda route: route.abort())
        await self.context.route("**/tracking**", lambda route: route.abort())
        await self.context.route(
            "**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort()
        )

        self.page = await self.context.new_page()

        # Override navigator properties to avoid detection
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en']});
        """
        )

        await setup_human_browser(self.page)

        # Visit homepage first
        console.print("[dim]Visiting REA homepage...[/dim]")
        try:
            await self.page.goto(
                self.BASE_URL, wait_until="domcontentloaded", timeout=30000
            )
            await simulate_reading(self.page, 3, 7)
        except Exception as e:
            console.print(f"[yellow]Homepage load issue: {e}[/yellow]")

    async def stop(self):
        if self.browser:
            await self.browser.close()

    def build_sold_url(self, suburb: str, page: int = 1) -> str:
        """Build search URL for sold listings on REA."""
        # e.g. https://www.realestate.com.au/sold/property-house-in-donvale,+vic+3111/list-1
        suburb_encoded = suburb.lower().replace(" ", "+")

        # Extract postcode if present
        postcode = ""
        match = re.search(r"(\d{4})$", suburb)
        if match:
            postcode = match.group(1)
            suburb_encoded = (
                suburb.replace(postcode, "").strip().lower().replace(" ", "+")
            )

        # Suburb to postcode mapping for core areas
        SUBURB_POSTCODES = {
            "doncaster": "3108",
            "doncaster east": "3109",
            "donvale": "3111",
            "templestowe": "3106",
            "templestowe lower": "3107",
            "bulleen": "3105",
        }
        if not postcode:
            postcode = SUBURB_POSTCODES.get(suburb.lower(), "")

        location = (
            f"{suburb_encoded},+vic+{postcode}"
            if postcode
            else f"{suburb_encoded},+vic"
        )
        url = f"{self.BASE_URL}/sold/property-house-in-{location}/list-{page}"
        return url

    async def scrape_sold(
        self, suburb: str, max_pages: int = 2
    ) -> list[dict[str, Any]]:
        """Scrape sold listings from REA."""
        listings = []
        page_num = 1
        console.print(f"[blue]Scraping REA (SOLD): {suburb}[/blue]")

        while page_num <= max_pages:
            url = self.build_sold_url(suburb, page_num)
            try:
                await random_delay(5, 12)
                await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)

                content = await self.page.content()
                if "blocked" in content.lower() or "challenge" in content.lower():
                    console.print("[red]Bot detection triggered on REA SOLD[/red]")
                    break

                await simulate_reading(self.page, 5, 10)

                cards = await self.page.query_selector_all(
                    '[class*="residential-card"]'
                )
                if not cards:
                    cards = await self.page.query_selector_all(
                        '[data-testid="listing-card"]'
                    )

                if not cards:
                    console.print(f"  No cards found on REA page {page_num}")
                    break

                for card in cards:
                    listing = await self._extract_listing(card, suburb)
                    if listing:
                        listings.append(listing)

                console.print(f"  Page {page_num}: {len(cards)} sold listings")
                page_num += 1
            except Exception as e:
                console.print(f"  [red]REA Sold Error: {e}[/red]")
                break

        return listings

    async def scrape_suburb(
        self, suburb: str, max_pages: int = 3
    ) -> list[dict[str, Any]]:
        """Scrape with extra caution for REA's bot detection."""
        listings = []
        page_num = 1

        console.print(f"[blue]Scraping REA: {suburb}[/blue]")

        while page_num <= max_pages:
            if self.session.should_take_break():
                console.print("[dim]Taking break (REA is strict)...[/dim]")
                await asyncio.sleep(random.uniform(60, 120))  # Longer breaks for REA

            url = self.build_search_url(suburb, page_num)

            try:
                # Longer pre-navigation delay for REA
                await random_delay(4, 10)

                await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)

                # Check for bot detection page
                content = await self.page.content()
                if (
                    "blocked" in content.lower()
                    or "captcha" in content.lower()
                    or "challenge" in content.lower()
                ):
                    console.print(
                        "[red]Bot detection triggered - stopping REA scrape[/red]"
                    )
                    break

                # Extended reading simulation
                await simulate_reading(self.page, 5, 12)

                # Natural scrolling
                for _ in range(random.randint(3, 6)):
                    await human_scroll(self.page)
                    await random_delay(1, 3)
                    await human_move_mouse(self.page)

                # Find listings
                cards = await self.page.query_selector_all(
                    '[class*="residential-card"]'
                )
                if not cards:
                    cards = await self.page.query_selector_all(
                        '[data-testid="listing-card"]'
                    )

                if not cards:
                    break

                for card in cards:
                    try:
                        listing = await self._extract_listing(card, suburb)
                        if listing:
                            listings.append(listing)
                    except Exception:
                        pass

                console.print(f"  Page {page_num}: {len(cards)} listings")

                page_num += 1

                # Very long delay between pages for REA
                await random_delay(8, 20)

            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")
                break

        console.print(f"  Total for {suburb}: {len(listings)}")
        return listings

    async def _extract_listing(self, card, suburb: str) -> dict[str, Any] | None:
        """Extract listing data."""
        try:
            link = await card.query_selector("a[href*='/property-']")
            if not link:
                return None

            href = await link.get_attribute("href")
            if not href:
                return None

            if not href.startswith("http"):
                href = f"{self.BASE_URL}{href}"

            # Extract ID
            match = re.search(r"-(\d+)$", href)
            listing_id = match.group(1) if match else None
            if not listing_id:
                return None

            text = await card.inner_text()
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            address = lines[0] if lines else ""

            # Better parsing for REA
            price_text = ""
            sold_date = None
            agent = ""
            agency = ""

            # Find price and sold date
            for i, line in enumerate(lines):
                line_low = line.lower()
                if "$" in line and not price_text:
                    price_text = line
                if "sold on" in line_low:
                    # Sold on 03 May 2025
                    date_match = re.search(
                        r"sold on\s*(\d{1,2}\s+[a-zA-Z]+\s+\d{4})", line_low
                    )
                    if date_match:
                        from datetime import datetime

                        try:
                            sold_date = datetime.strptime(
                                date_match.group(1), "%d %b %Y"
                            ).isoformat()
                        except Exception:
                            pass

            # Logic for Agent/Agency from REA cards is tricky as they are often separate elements
            # But sometimes they are in text or we can check siblings
            branding = await card.query_selector('[class*="branding"]')
            if branding:
                agency_text = (
                    await branding.get_attribute("aria-label")
                    or await branding.inner_text()
                )
                agency = agency_text.strip() if agency_text else ""

            # Use Delegator for rich features in REA as well
            from scanner.utils.delegator import delegate_extraction

            rich_features = delegate_extraction(text)

            # Features
            beds = baths = cars = None
            for line in lines:
                line_low = line.lower()
                if "bed" in line_low:
                    m = re.search(r"(\d+)", line)
                    beds = int(m.group(1)) if m else None
                if "bath" in line_low:
                    m = re.search(r"(\d+)", line)
                    baths = int(m.group(1)) if m else None
                if "car" in line_low:
                    m = re.search(r"(\d+)", line)
                    cars = int(m.group(1)) if m else None

            land_size = rich_features.get("land_size_m2")
            if not land_size:
                land_match = re.search(r"(\d{3,})\s*m[²2]", text)
                if land_match:
                    land_size = float(land_match.group(1))

            prop_type = rich_features.get("property_type", "House")
            if "land" in href.lower() or "land" in text.lower():
                prop_type = "Land"

            return {
                "listing_id": listing_id,
                "source": "rea",
                "url": href,
                "address": address,
                "suburb": suburb,
                "price_text": price_text,
                "property_type": prop_type,
                "bedrooms": beds,
                "bathrooms": baths,
                "car_spaces": cars,
                "land_size_m2": land_size,
                "sold_date": sold_date,
                "agent": agent,
                "agency": agency,
                "finish_quality": rich_features.get("finish_quality", "Standard"),
                "renovated": rich_features.get("renovated", False),
                "year_built": rich_features.get("year_built_estimate"),
                "features": rich_features.get("features", []),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception:
            return None

    def parse_price(
        self, price_text: str
    ) -> tuple[float | None, float | None, float | None]:
        if not price_text:
            return None, None, None

        price_text = price_text.lower().replace(",", "").replace("$", "")

        range_match = re.search(r"([\d.]+)\s*m?\s*[-–]+\s*([\d.]+)\s*m?", price_text)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            if low < 100:
                low *= 1_000_000
            if high < 100:
                high *= 1_000_000
            return low, high, (low + high) / 2

        single_match = re.search(r"([\d.]+)\s*m", price_text)
        if single_match:
            value = float(single_match.group(1)) * 1_000_000
            return value, value, value

        num_match = re.search(r"(\d{6,})", price_text)
        if num_match:
            value = float(num_match.group(1))
            return value, value, value

        return None, None, None


async def scrape_rea(suburbs: list[str] | None = None) -> int:
    """Scrape REA with extreme caution."""
    config = get_config()
    suburbs = suburbs or config.suburbs

    if not suburbs:
        return 0

    # Very conservative - only 2 suburbs per run for REA
    max_suburbs = 2
    if len(suburbs) > max_suburbs:
        console.print(
            f"[dim]REA: Limiting to {max_suburbs} suburbs (strict bot detection)[/dim]"
        )
        suburbs = random.sample(suburbs, max_suburbs)

    scraper = REAScraper()

    try:
        await scraper.start()

        total_new = 0

        for suburb in suburbs:
            listings = await scraper.scrape_suburb(suburb, max_pages=2)

            with get_session() as session:
                for listing in listings:
                    if any(
                        kw in listing.get("address", "").lower()
                        for kw in config.filters.exclude_keywords
                    ):
                        continue

                    listing_id = listing["listing_id"]
                    raw_id = f"rea:{listing_id}"

                    existing = session.query(RawListing).filter_by(id=raw_id).first()
                    if existing:
                        existing.fetched_at = datetime.now(timezone.utc)
                        existing.payload = listing
                        continue

                    raw = RawListing(
                        id=raw_id,
                        source="rea",
                        listing_id=listing_id,
                        url=listing["url"],
                        payload=listing,
                    )
                    session.add(raw)

                    site = (
                        session.query(Site).filter_by(rea_listing_id=listing_id).first()
                    )
                    if not site:
                        price_low, price_high, price_guide = scraper.parse_price(
                            listing.get("price_text", "")
                        )

                        site = Site(
                            source="rea",
                            rea_listing_id=listing_id,
                            url=listing["url"],
                            address_raw=listing.get("address"),
                            suburb=listing.get("suburb"),
                            state="VIC",
                            property_type=listing.get("property_type", "house"),
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
                        site.last_seen = datetime.now(timezone.utc)
            # Very long break between suburbs for REA
            await random_delay(30, 60)

        console.print(f"[green]REA: {total_new} new listings[/green]")
        return total_new

    finally:
        await scraper.stop()


async def scrape_sold_rea(suburbs: list[str] | None = None, max_pages: int = 1):
    """Scrape only SOLD listings from REA."""
    config = get_config()
    suburbs = suburbs or config.suburbs

    if not suburbs:
        return 0

    scraper = REAScraper()
    try:
        await scraper.start()
        total_saved = 0

        for suburb in suburbs:
            sold_listings = await scraper.scrape_sold(suburb, max_pages=max_pages)

            from scanner.market.models import SessionLocal as MarketSessionLocal

            with MarketSessionLocal() as db:
                for sold in sold_listings:
                    price_val = parse_sold_price(sold.get("price_text", ""))
                    if price_val:
                        sold["sold_price"] = price_val
                        save_comparable(db, sold)
                        total_saved += 1

            await random_delay(30, 60)

        console.print(
            f"[green]REA Sold: {total_saved} listings saved to market database.[/green]"
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
    parser.add_argument("--limit", type=int, default=2, help="Max pages to scrape")
    args = parser.parse_args()

    suburbs = [args.suburb] if args.suburb else None

    if args.type == "sold":
        asyncio.run(scrape_sold_rea(suburbs, max_pages=args.limit))
    else:
        asyncio.run(scrape_rea(suburbs))


if __name__ == "__main__":
    run()
