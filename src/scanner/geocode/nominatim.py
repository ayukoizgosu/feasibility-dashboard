"""Nominatim (OpenStreetMap) geocoder - FREE, no API key required."""

import asyncio
import time
from datetime import datetime
from typing import Any

import httpx
from rich.console import Console

from scanner.config import get_config
from scanner.models import Site, GeocodingLog
from scanner.db import get_session

console = Console()


class NominatimGeocoder:
    """Free geocoder using OpenStreetMap's Nominatim service.
    
    Rate limit: 1 request per second (required by Nominatim usage policy).
    """
    
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    
    def __init__(self):
        self.config = get_config()
        self.last_request_time = 0.0
        self.daily_count = 0
    
    async def geocode(self, address: str, suburb: str = "", state: str = "VIC") -> dict[str, Any]:
        """Geocode an address.
        
        Returns dict with: lat, lon, confidence, display_name, error
        """
        # Rate limiting - 1 request per second
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        
        # Build full address
        full_address = address
        if suburb and suburb.lower() not in address.lower():
            full_address = f"{address}, {suburb}"
        if state and state.lower() not in address.lower():
            full_address = f"{full_address}, {state}, Australia"
        else:
            full_address = f"{full_address}, Australia"
        
        params = {
            "q": full_address,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "countrycodes": "au"
        }
        
        headers = {
            "User-Agent": "SiteScanner/1.0 (property-research-tool)"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=10.0
                )
                self.last_request_time = time.time()
                self.daily_count += 1
                
                if response.status_code != 200:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "confidence": 0.0
                    }
                
                results = response.json()
                
                if not results:
                    return {
                        "error": "No results found",
                        "confidence": 0.0
                    }
                
                result = results[0]
                
                # Calculate confidence from importance score
                importance = float(result.get("importance", 0.5))
                match_type = result.get("type", "")
                
                # Boost confidence for building/house matches
                confidence = importance
                if match_type in ["house", "building", "residential"]:
                    confidence = min(1.0, confidence + 0.2)
                elif match_type in ["street", "road"]:
                    confidence = max(0.3, confidence - 0.2)
                
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "display_name": result.get("display_name", ""),
                    "confidence": round(confidence, 3),
                    "type": match_type,
                    "error": None
                }
                
        except httpx.TimeoutException:
            return {"error": "Timeout", "confidence": 0.0}
        except Exception as e:
            return {"error": str(e), "confidence": 0.0}


async def geocode_pending_sites(limit: int = 500) -> tuple[int, int]:
    """Geocode all pending sites.
    
    Returns: (success_count, failure_count)
    """
    geocoder = NominatimGeocoder()
    success = 0
    failed = 0
    
    with get_session() as session:
        # Get pending sites
        pending = session.query(Site).filter(
            Site.geocode_status == "pending"
        ).limit(limit).all()
        
        if not pending:
            console.print("[yellow]No pending sites to geocode[/yellow]")
            return 0, 0
        
        console.print(f"[blue]Geocoding {len(pending)} sites with Nominatim (free)...[/blue]")
        console.print("[dim]Rate limit: 1 request/second[/dim]")
        
        for i, site in enumerate(pending):
            if not site.address_raw:
                site.geocode_status = "failed"
                site.review_reason = "No address"
                failed += 1
                continue
            
            result = await geocoder.geocode(
                site.address_raw,
                site.suburb or "",
                site.state or "VIC"
            )
            
            if result.get("error"):
                site.geocode_status = "failed"
                site.review_reason = f"Geocode error: {result['error']}"
                failed += 1
            elif result.get("confidence", 0) < 0.4:
                site.lat = result.get("lat")
                site.lon = result.get("lon")
                site.geocode_provider = "nominatim"
                site.geocode_confidence = result.get("confidence")
                site.geocode_status = "low_confidence"
                site.requires_manual_review = True
                site.review_reason = "Low geocode confidence"
                failed += 1
            else:
                site.lat = result["lat"]
                site.lon = result["lon"]
                site.geocode_provider = "nominatim"
                site.geocode_confidence = result["confidence"]
                site.geocode_status = "success"
                site.address_norm = result.get("display_name", site.address_raw)
                success += 1
            
            # Progress update every 50
            if (i + 1) % 50 == 0:
                console.print(f"  Progress: {i + 1}/{len(pending)}")
                session.commit()  # Save progress
        
        # Update daily log
        today = datetime.utcnow().strftime("%Y-%m-%d")
        log = session.query(GeocodingLog).filter_by(
            provider="nominatim",
            date=today
        ).first()
        
        if log:
            log.count += success + failed
        else:
            log = GeocodingLog(provider="nominatim", date=today, count=success + failed)
            session.add(log)
    
    console.print(f"[green]Geocoding complete: {success} success, {failed} failed[/green]")
    return success, failed


def run():
    """Entry point for make geocode."""
    asyncio.run(geocode_pending_sites())


if __name__ == "__main__":
    run()
