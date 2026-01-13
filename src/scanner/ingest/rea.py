"""realestate.com.au scraper with human-like behavior.

WARNING: REA uses Kasada bot protection which is aggressive.
This scraper includes extensive evasion techniques but may still get blocked.
Consider using Domain as primary source.
"""

import asyncio
import random
import re
from datetime import datetime
from typing import Any

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from rich.console import Console

from scanner.config import get_config
from scanner.models import RawListing, Site
from scanner.db import get_session
from scanner.ingest.human_like import (
    random_delay, human_scroll, human_move_mouse,
    setup_human_browser, simulate_reading, SessionManager
)

console = Console()


class REAScraper:
    """Human-like scraper for realestate.com.au."""
    
    BASE_URL = "https://www.realestate.com.au"
    
    def __init__(self):
        self.config = get_config()
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.session = SessionManager(max_pages_per_session=20)  # More conservative for REA
    
    async def start(self):
        """Start browser with stealth settings."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        
        # Realistic context
        self.context = await self.browser.new_context(
            viewport={"width": 1536, "height": 864},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-AU",
            timezone_id="Australia/Melbourne",
            geolocation={"latitude": -37.8136, "longitude": 144.9631},  # Melbourne
            permissions=["geolocation"]
        )
        
        # Block trackers
        await self.context.route("**/analytics**", lambda route: route.abort())
        await self.context.route("**/tracking**", lambda route: route.abort())
        await self.context.route("**/*.{png,jpg,jpeg,gif,svg}", lambda route: route.abort())
        
        self.page = await self.context.new_page()
        
        # Override navigator properties to avoid detection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en']});
        """)
        
        await setup_human_browser(self.page)
        
        # Visit homepage first
        console.print("[dim]Visiting REA homepage...[/dim]")
        try:
            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await simulate_reading(self.page, 3, 7)
        except Exception as e:
            console.print(f"[yellow]Homepage load issue: {e}[/yellow]")
    
    async def stop(self):
        if self.browser:
            await self.browser.close()
    
    def build_search_url(self, suburb: str, page: int = 1) -> str:
        """Build REA search URL."""
        property_types = []
        for pt in self.config.filters.property_types:
            if pt == "house":
                property_types.append("house")
            elif pt == "vacant_land":
                property_types.append("land")
        
        suburb_slug = suburb.lower().replace(" ", "-")
        ptype_str = "-".join(property_types) if property_types else "house"
        
        # REA URL structure
        url = f"{self.BASE_URL}/buy/property-{ptype_str}-with-studio-between-0-{self.config.filters.price_max}-in-{suburb_slug}%2c+vic/list-{page}"
        
        return url
    
    async def scrape_suburb(self, suburb: str, max_pages: int = 3) -> list[dict[str, Any]]:
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
                if "blocked" in content.lower() or "captcha" in content.lower() or "challenge" in content.lower():
                    console.print("[red]Bot detection triggered - stopping REA scrape[/red]")
                    break
                
                # Extended reading simulation
                await simulate_reading(self.page, 5, 12)
                
                # Natural scrolling
                for _ in range(random.randint(3, 6)):
                    await human_scroll(self.page)
                    await random_delay(1, 3)
                    await human_move_mouse(self.page)
                
                # Find listings
                cards = await self.page.query_selector_all('[class*="residential-card"]')
                if not cards:
                    cards = await self.page.query_selector_all('[data-testid="listing-card"]')
                
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
            match = re.search(r'-(\d+)$', href)
            listing_id = match.group(1) if match else None
            if not listing_id:
                return None
            
            text = await card.inner_text()
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            address = lines[0] if lines else ""
            
            price_text = ""
            for line in lines:
                if '$' in line:
                    price_text = line
                    break
            
            # Features
            beds = baths = cars = None
            for line in lines:
                if 'bed' in line.lower():
                    m = re.search(r'(\d+)', line)
                    beds = int(m.group(1)) if m else None
                if 'bath' in line.lower():
                    m = re.search(r'(\d+)', line)
                    baths = int(m.group(1)) if m else None
                if 'car' in line.lower():
                    m = re.search(r'(\d+)', line)
                    cars = int(m.group(1)) if m else None
            
            land_size = None
            land_match = re.search(r'(\d{3,})\s*m[²2]', text)
            if land_match:
                land_size = float(land_match.group(1))
            
            prop_type = "house"
            if "land" in href.lower():
                prop_type = "vacant_land"
            
            return {
                "listing_id": listing_id,
                "url": href,
                "address": address,
                "suburb": suburb,
                "price_text": price_text,
                "property_type": prop_type,
                "bedrooms": beds,
                "bathrooms": baths,
                "car_spaces": cars,
                "land_size_m2": land_size,
                "scraped_at": datetime.utcnow().isoformat()
            }
            
        except Exception:
            return None
    
    def parse_price(self, price_text: str) -> tuple[float | None, float | None, float | None]:
        if not price_text:
            return None, None, None
        
        price_text = price_text.lower().replace(",", "").replace("$", "")
        
        range_match = re.search(r'([\d.]+)\s*m?\s*[-–]+\s*([\d.]+)\s*m?', price_text)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            if low < 100:
                low *= 1_000_000
            if high < 100:
                high *= 1_000_000
            return low, high, (low + high) / 2
        
        single_match = re.search(r'([\d.]+)\s*m', price_text)
        if single_match:
            value = float(single_match.group(1)) * 1_000_000
            return value, value, value
        
        num_match = re.search(r'(\d{6,})', price_text)
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
        console.print(f"[dim]REA: Limiting to {max_suburbs} suburbs (strict bot detection)[/dim]")
        suburbs = random.sample(suburbs, max_suburbs)
    
    scraper = REAScraper()
    
    try:
        await scraper.start()
        
        total_new = 0
        
        for suburb in suburbs:
            listings = await scraper.scrape_suburb(suburb, max_pages=2)
            
            with get_session() as session:
                for listing in listings:
                    if any(kw in listing.get("address", "").lower() 
                           for kw in config.filters.exclude_keywords):
                        continue
                    
                    listing_id = listing["listing_id"]
                    raw_id = f"rea:{listing_id}"
                    
                    existing = session.query(RawListing).filter_by(id=raw_id).first()
                    if existing:
                        existing.fetched_at = datetime.utcnow()
                        existing.payload = listing
                        continue
                    
                    raw = RawListing(
                        id=raw_id,
                        source="rea",
                        listing_id=listing_id,
                        url=listing["url"],
                        payload=listing
                    )
                    session.add(raw)
                    
                    site = session.query(Site).filter_by(rea_listing_id=listing_id).first()
                    if not site:
                        price_low, price_high, price_guide = scraper.parse_price(listing.get("price_text", ""))
                        
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
                            geocode_status="pending"
                        )
                        session.add(site)
                        total_new += 1
                    else:
                        site.last_seen = datetime.utcnow()
            
            # Very long break between suburbs for REA
            await random_delay(30, 60)
        
        console.print(f"[green]REA: {total_new} new listings[/green]")
        return total_new
        
    finally:
        await scraper.stop()


def run():
    asyncio.run(scrape_rea())


if __name__ == "__main__":
    run()
