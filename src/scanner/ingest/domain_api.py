"""Domain API client for listings ingestion.

This uses the official Domain API which is the sustainable, ToS-compliant approach.
Sandbox tier provides test data; Production tier provides live listings.

Rate limits:
- Sandbox: 500 calls/day (test data only)
- Production: varies by subscription tier
"""

import asyncio
from datetime import datetime
from typing import Any
import base64

import httpx
from rich.console import Console

from scanner.config import get_config
from scanner.models import RawListing, Site
from scanner.db import get_session

console = Console()


class DomainAPIClient:
    """Client for Domain's official API."""
    
    AUTH_URL = "https://auth.domain.com.au/v1/connect/token"
    API_BASE = "https://api.domain.com.au/v1"
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.config = get_config()
        self.client_id = client_id or self.config.settings.domain_client_id
        self.client_secret = client_secret or self.config.settings.domain_client_secret
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    async def _ensure_token(self) -> bool:
        """Get or refresh access token."""
        if not self.client_id or not self.client_secret:
            console.print("[red]Domain API credentials not configured[/red]")
            console.print("[yellow]Set DOMAIN_CLIENT_ID and DOMAIN_CLIENT_SECRET in .env[/yellow]")
            return False
        
        # Check if token still valid
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return True
        
        # Request new token
        try:
            response = await self._client.post(
                self.AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "scope": "api_listings_read"
                },
                auth=(self.client_id, self.client_secret)
            )
            
            if response.status_code != 200:
                console.print(f"[red]Auth failed: {response.status_code}[/red]")
                return False
            
            data = response.json()
            self.access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            return True
            
        except Exception as e:
            console.print(f"[red]Auth error: {e}[/red]")
            return False
    
    async def search_listings(
        self, 
        suburbs: list[str],
        property_types: list[str] = None,
        price_max: int = None,
        land_size_min: int = None,
        page_size: int = 100
    ) -> list[dict]:
        """Search for listings matching criteria."""
        
        if not await self._ensure_token():
            return []
        
        config = self.config
        property_types = property_types or config.filters.property_types
        price_max = price_max or config.filters.price_max
        land_size_min = land_size_min or config.filters.land_size_min_m2
        
        # Map property types to Domain API format
        type_map = {
            "house": "House",
            "vacant_land": "VacantLand"
        }
        api_types = [type_map.get(t, t) for t in property_types]
        
        all_listings = []
        
        for suburb in suburbs:
            console.print(f"[blue]Searching Domain API: {suburb}[/blue]")
            
            search_params = {
                "listingType": "Sale",
                "propertyTypes": api_types,
                "locations": [
                    {
                        "suburb": suburb,
                        "state": "VIC",
                        "includeSurroundingSuburbs": False
                    }
                ],
                "maxPrice": price_max,
                "minLandArea": land_size_min,
                "pageSize": page_size
            }
            
            try:
                response = await self._client.post(
                    f"{self.API_BASE}/listings/residential/_search",
                    json=search_params,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                
                if response.status_code == 200:
                    listings = response.json()
                    console.print(f"  Found {len(listings)} listings")
                    all_listings.extend(listings)
                elif response.status_code == 429:
                    console.print("[yellow]Rate limit hit - stopping[/yellow]")
                    break
                else:
                    console.print(f"[yellow]Search failed: {response.status_code}[/yellow]")
                
                await asyncio.sleep(0.5)  # Respect rate limits
                
            except Exception as e:
                console.print(f"[red]Search error: {e}[/red]")
        
        return all_listings
    
    async def get_listing_details(self, listing_id: str) -> dict | None:
        """Get detailed info for a specific listing."""
        
        if not await self._ensure_token():
            return None
        
        try:
            response = await self._client.get(
                f"{self.API_BASE}/listings/{listing_id}",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                console.print("[yellow]Rate limit hit[/yellow]")
            
        except Exception as e:
            console.print(f"[yellow]Details error: {e}[/yellow]")
        
        return None


def parse_domain_listing(listing: dict) -> dict:
    """Parse Domain API listing into normalized format."""
    
    # Extract address
    address_parts = listing.get("addressParts", {})
    address = listing.get("address", "")
    
    # Extract price
    price_details = listing.get("priceDetails", {})
    price_display = price_details.get("displayPrice", "")
    price_value = price_details.get("price")
    
    # Extract land size
    land_area = None
    area_info = listing.get("landAreaSqm")
    if area_info:
        land_area = area_info
    
    return {
        "listing_id": str(listing.get("id")),
        "url": listing.get("listingSlug", ""),
        "address": address,
        "street_number": address_parts.get("streetNumber"),
        "street_name": address_parts.get("streetName"),
        "suburb": address_parts.get("suburb"),
        "postcode": address_parts.get("postcode"),
        "state": address_parts.get("state", "VIC"),
        "price_display": price_display,
        "price_guide": price_value,
        "property_type": listing.get("propertyTypes", [None])[0],
        "bedrooms": listing.get("bedrooms"),
        "bathrooms": listing.get("bathrooms"),
        "car_spaces": listing.get("carspaces"),
        "land_size_m2": land_area,
        "headline": listing.get("headline"),
        "description": listing.get("description"),
        "agent": listing.get("advertiserIdentifiers", {}).get("agentName"),
        "agency": listing.get("advertiserIdentifiers", {}).get("advertiserName")
    }


async def ingest_domain_api(suburbs: list[str] = None) -> int:
    """Ingest listings from Domain API."""
    config = get_config()
    suburbs = suburbs or config.suburbs
    
    if not config.settings.domain_client_id:
        console.print("[yellow]Domain API not configured - skipping[/yellow]")
        console.print("[dim]To enable: set DOMAIN_CLIENT_ID and DOMAIN_CLIENT_SECRET in .env[/dim]")
        return 0
    
    async with DomainAPIClient() as client:
        listings = await client.search_listings(suburbs)
        
        if not listings:
            console.print("[yellow]No listings found from Domain API[/yellow]")
            return 0
        
        new_count = 0
        with get_session() as session:
            for listing in listings:
                parsed = parse_domain_listing(listing)
                listing_id = parsed["listing_id"]
                
                # Skip excluded keywords
                if any(kw in parsed.get("address", "").lower() 
                       for kw in config.filters.exclude_keywords):
                    continue
                
                raw_id = f"domain:{listing_id}"
                
                # Check if exists
                existing = session.query(RawListing).filter_by(id=raw_id).first()
                if existing:
                    existing.fetched_at = datetime.utcnow()
                    existing.payload = listing
                    continue
                
                # Create raw listing
                raw = RawListing(
                    id=raw_id,
                    source="domain",
                    listing_id=listing_id,
                    url=parsed.get("url"),
                    payload=listing
                )
                session.add(raw)
                
                # Create site
                site = session.query(Site).filter_by(domain_listing_id=listing_id).first()
                if not site:
                    site = Site(
                        source="domain",
                        domain_listing_id=listing_id,
                        url=parsed.get("url"),
                        address_raw=parsed.get("address"),
                        street_number=parsed.get("street_number"),
                        street_name=parsed.get("street_name"),
                        suburb=parsed.get("suburb"),
                        postcode=parsed.get("postcode"),
                        state="VIC",
                        property_type=parsed.get("property_type"),
                        price_display=parsed.get("price_display"),
                        price_guide=parsed.get("price_guide"),
                        bedrooms=parsed.get("bedrooms"),
                        bathrooms=parsed.get("bathrooms"),
                        car_spaces=parsed.get("car_spaces"),
                        land_size_listed=parsed.get("land_size_m2"),
                        geocode_status="pending"
                    )
                    session.add(site)
                    new_count += 1
                else:
                    site.last_seen = datetime.utcnow()
        
        console.print(f"[green]Domain API: {new_count} new listings[/green]")
        return new_count


async def run_domain():
    """Entry point."""
    from scanner.db import init_db
    init_db()
    await ingest_domain_api()


def run():
    asyncio.run(run_domain())


if __name__ == "__main__":
    run()
