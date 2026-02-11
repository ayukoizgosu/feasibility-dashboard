import sys

import requests


def debug_domain():
    # URL for Donvale, >3000sqm
    url = "https://www.domain.com.au/sale/donvale-vic-3111/?landsize-min=3000"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        with open("debug_domain.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Saved to debug_domain.html")

        if "captcha" in resp.text.lower():
            print("CAPTCHA detected!")
        if "access denied" in resp.text.lower():
            print("Access Denied detected!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_domain()
if __name__ == "__main__":
    debug_domain()
