import asyncio

from playwright.async_api import async_playwright


async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        url = "https://www.domain.com.au/sold-listings/doncaster-vic-3108/?ptype=house,vacant-land&excludepricewithheld=1"
        print(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            content = await page.content()

            with open("debug_domain_playwright.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved debug_domain_playwright.html")

            # Check selectors
            cards = await page.query_selector_all('[data-testid="listing-card"]')
            print(f"Found {len(cards)} cards with primary selector")

            cards2 = await page.query_selector_all('[class*="listing-result"]')
            print(f"Found {len(cards2)} cards with secondary selector")

        except Exception as e:
            print(f"Error: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug())
if __name__ == "__main__":
    asyncio.run(debug())
