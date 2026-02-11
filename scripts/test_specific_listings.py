import asyncio
import os
import sys

from playwright.async_api import async_playwright

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from scanner.utils.delegator import delegate_extraction

PROPERTIES = [
    {
        "address": "25 Sample Street, Donvale",
        "url": "https://www.domain.com.au/property-profile/25-sample-street-donvale-vic-3111",
    },
    {
        "address": "10 Test Avenue, Melbourne",
        "url": "https://www.domain.com.au/property-profile/10-test-avenue-melbourne-vic-3000",
    },
]


async def scrape_and_assess():
    async with async_playwright() as p:
        # Use a stealthy context similar to domain.py
        browser = await p.chromium.launch(
            headless=True, args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for prop in PROPERTIES:
            print(f"\n--- Processing: {prop['address']} ---")
            print(f"URL: {prop['url']}")

            try:
                await page.goto(
                    prop["url"], wait_until="domcontentloaded", timeout=60000
                )

                # Domain Property Profile content extraction
                # Description is usually in a div with class css-1nxgjc7 or similar, or just paragraphs
                # We'll grab the full text of the main content area

                # Try to click "Read more" if it exists
                try:
                    read_more = await page.query_selector(
                        'button:has-text("Read more")'
                    )
                    if read_more:
                        await read_more.click()
                        await asyncio.sleep(1)
                except:
                    pass

                # Get description text
                description = None

                # Check for standard description container
                content_div = await page.query_selector(
                    '[data-testid="description-wrapper"]'
                )
                if content_div:
                    description = await content_div.inner_text()

                if not description:
                    # Fallback to body text accumulation
                    body = await page.inner_text("body")
                    # simplistic extraction: look for block of text
                    description = body[:4000]  # Cap it

                print(
                    f"Extracted Description Length: {len(description) if description else 0}"
                )
                if description and len(description) > 100:
                    print(f"Snippet: {description[:200]}...")

                    # Run Analysis
                    print("Running Quality Assessment...")
                    result = delegate_extraction(description)

                    print(f"Assessment Result:")
                    print(f"  Quality: {result.get('finish_quality')}")
                    print(
                        f"  Condition: {'Renovated' if result.get('renovated') else 'Original/Unknown'}"
                    )
                    print(f"  Key Features: {result.get('features')}")
                else:
                    print("Failed to extract meaningful description.")

            except Exception as e:
                print(f"Error processing {prop['address']}: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_and_assess())
