"""Planning permit data fetching and analysis."""

import re
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from sqlalchemy import select
from sqlalchemy.orm import Session

from scanner.models import PlanningApplication

console = Console()


class PlanningAlertsClient:
    """Client for fetching data from PlanningAlerts.org.au via HTML scraping."""

    BASE_URL = "https://www.planningalerts.org.au"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
    }

    def __init__(self, db_session: Session):
        self.session = db_session

    def fetch_for_address(self, address_query: str) -> list[PlanningApplication]:
        """Fetch applications for a specific address.

        Args:
            address_query: Full address string (e.g. "10 Smith St, Collingwood VIC")

        Returns:
            List of PlanningApplication objects (persisted to DB)
        """
        search_url = f"{self.BASE_URL}/applications?address={requests.utils.quote(address_query)}"
        console.print(f"[dim]Scraping PlanningAlerts: {search_url}[/dim]")

        try:
            # Be polite
            time.sleep(1.0)

            resp = requests.get(search_url, headers=self.HEADERS, timeout=15)
            if resp.status_code != 200:
                console.print(
                    f"[red]PlanningAlerts returned status {resp.status_code}[/red]"
                )
                return []

            return self._parse_results(resp.text)

        except Exception as e:
            console.print(f"[red]Failed to fetch planning data: {e}[/red]")
            return []

    def _parse_results(self, html_content: str) -> list[PlanningApplication]:
        """Parse HTML search results into models."""
        soup = BeautifulSoup(html_content, "html.parser")
        apps = []

        # Helper to clean text
        def clean(t):
            return t.strip() if t else ""

        for item in soup.find_all("div", class_="application"):
            try:
                # 1. Address
                address_tag = item.find("div", class_="address")
                address = (
                    clean(address_tag.get_text()) if address_tag else "Unknown Address"
                )

                # 2. Description
                desc_tag = item.find("p", class_="description") or item.find(
                    "div", class_="description"
                )
                description = clean(desc_tag.get_text()) if desc_tag else ""

                # 3. Info link (contains ID)
                link_tag = item.find("a", href=True)
                info_url = f"{self.BASE_URL}{link_tag['href']}" if link_tag else ""

                # Extract Council and App Number from footer/meta if available
                # Logic varies, usually: "Application no. XXXXX • City of Yarra"
                meta_text = item.get_text()

                # Try to extract application number
                app_no = "Unknown"
                council = "Unknown"

                # Simple heuristcs for now
                council_tag = item.find("div", class_="authority")
                if council_tag:
                    council = clean(council_tag.get_text())

                # Create Model
                app = PlanningApplication(
                    application_number=(
                        info_url.split("/")[-1] if info_url else "unknown"
                    ),  # Fallback ID
                    address_text=address,
                    description=description,
                    council_name=council,
                    info_url=info_url,
                    # HTML list view often lacks these, might need detail fetch if crucial
                    status="Submitted",
                    received_date=datetime.now(),  # Placeholder
                )

                # Upsert logic (simplistic)
                existing = self.session.scalar(
                    select(PlanningApplication).where(
                        PlanningApplication.info_url == app.info_url
                    )
                )

                if not existing:
                    self.session.add(app)
                    apps.append(app)
                else:
                    # Update potentially changed fields?
                    pass

            except Exception as e:
                console.print(f"[yellow]Failed to parse application item: {e}[/yellow]")
                continue

        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            console.print(f"[red]DB Commit failed: {e}[/red]")

        return apps
