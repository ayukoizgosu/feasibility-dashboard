import re
import time

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}


def check_planningalerts():
    # Use a real address search URL
    url = "https://www.planningalerts.org.au/applications?address=Doncaster+East+VIC"
    print(f"\nChecking PlanningAlerts: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            # Simple regex to check for application items
            # In HTML, they usually look like <div class="application">...</div> or similar
            # Let's just look for the text "Construction" or "Permit" which would indicate content
            content_sample = resp.text[:500]
            print(f"Response start: {content_sample}...")

            app_count = len(re.findall(r'class="application', resp.text))
            hidden_email = len(re.findall(r"cdn-cgi/l/email-protection", resp.text))

            print(f"Found {app_count} 'application' class matches.")
            print(f"Cloudflare email protection found: {hidden_email > 0}")

            if "Cloudflare" in resp.text:
                print("WARNING: Cloudflare protection detected.")

            if app_count > 0:
                print("SUCCESS: Content appears accessible via scraping.")
            else:
                print(
                    "WARNING: Page loaded but no applications found (might be empty result or different structure)."
                )
        else:
            print("Failed to access PlanningAlerts.")
    except Exception as e:
        print(f"Error: {e}")


def check_manningham():
    url = "https://www.manningham.vic.gov.au/planning-register"
    print(f"\nChecking Manningham Council: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")

        text_lower = resp.text.lower()
        if "greenlight" in text_lower:
            print("Detected 'Greenlight' software keyword.")
        elif "authority" in text_lower:
            print("Detected 'Authority' software keyword.")
        elif "objective" in text_lower:
            print("Detected 'Objective/Trapeze' software keyword.")
        elif "eservices" in text_lower:
            print("Detected 'eServices' software keyword.")
        else:
            print("No common software keyword detected. Saving snippet.")
            print(resp.text[:300])

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_planningalerts()
    print("-" * 30)
    check_manningham()
