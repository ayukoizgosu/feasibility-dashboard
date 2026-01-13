"""Human-like browser behavior utilities for scraping."""

import asyncio
import random
import re
from typing import Any

from playwright.async_api import Page


async def random_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    """Wait a random amount of time like a human would."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def human_scroll(page: Page, direction: str = "down", amount: int = None):
    """Scroll the page like a human - with variable speed and pauses."""

    viewport = page.viewport_size
    if not viewport:
        viewport = {"height": 800}

    if amount is None:
        # Random scroll amount
        amount = random.randint(200, viewport["height"])

    if direction == "down":
        delta = amount
    else:
        delta = -amount

    # Scroll in chunks with slight delays (human-like)
    chunks = random.randint(2, 5)
    chunk_size = delta // chunks

    for _ in range(chunks):
        await page.mouse.wheel(0, chunk_size)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def human_move_mouse(page: Page, x: int = None, y: int = None):
    """Move mouse in a natural curved path."""

    viewport = page.viewport_size
    if not viewport:
        return

    if x is None:
        x = random.randint(100, viewport.get("width", 1200) - 100)
    if y is None:
        y = random.randint(100, viewport.get("height", 800) - 100)

    # Move with small steps
    steps = random.randint(5, 15)
    await page.mouse.move(x, y, steps=steps)


async def human_type(page: Page, selector: str, text: str):
    """Type text with human-like delays between keystrokes."""

    await page.click(selector)
    await random_delay(0.2, 0.5)

    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))


async def setup_human_browser(page: Page):
    """Configure browser to appear more human-like."""

    # Randomize viewport slightly
    widths = [1366, 1440, 1536, 1920]
    heights = [768, 900, 864, 1080]

    width = random.choice(widths)
    height = random.choice(heights)

    await page.set_viewport_size({"width": width, "height": height})

    # Set common user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Can't change UA after page is created, but we can set extra headers
    await page.set_extra_http_headers(
        {
            "Accept-Language": "en-AU,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
    )


async def simulate_reading(page: Page, min_sec: float = 2.0, max_sec: float = 8.0):
    """Simulate a human reading/viewing the page."""

    # Random mouse movements while "reading"
    for _ in range(random.randint(1, 3)):
        await human_move_mouse(page)
        await random_delay(0.5, 1.5)

    # Small scrolls
    for _ in range(random.randint(0, 2)):
        await human_scroll(page, amount=random.randint(100, 300))
        await random_delay(0.5, 1.0)

    # Final pause
    await random_delay(min_sec, max_sec)


class SessionManager:
    """Manage browsing sessions to appear natural."""

    def __init__(self, max_pages_per_session: int = 50):
        self.max_pages = max_pages_per_session
        self.page_count = 0
        self.session_start = None

    def should_take_break(self) -> bool:
        """Check if we should pause to avoid detection."""
        self.page_count += 1

        # Take break every N pages
        if self.page_count >= self.max_pages:
            self.page_count = 0
            return True

        # Random chance of taking a break
        if random.random() < 0.02:  # 2% chance per page
            return True

        return False

    async def take_break(self):
        """Take a longer break to appear human."""
        break_time = random.uniform(30, 90)  # 30-90 seconds
        await asyncio.sleep(break_time)


# Patterns that indicate honeypot/trap links
HONEYPOT_PATTERNS = [
    r"subscribe",
    r"newsletter",
    r"saved.?search",
    r"alert",
    r"sign.?in",
    r"login",
    r"register",
    r"email.?this",
    r"share.?via.?email",
    r"hidden",
    r"trap",
]


def is_honeypot_link(href: str, text: str = "") -> bool:
    """Detect likely honeypot links that normal users never click.

    Args:
        href: The link URL
        text: The visible link text

    Returns:
        True if the link appears to be a honeypot
    """
    combined = f"{href} {text}".lower()

    for pattern in HONEYPOT_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True

    # Check for hidden/invisible elements (often honeypots)
    if "display:none" in combined or "visibility:hidden" in combined:
        return True

    return False


def generate_session_profile() -> dict:
    """Generate a realistic browsing session profile.

    Returns:
        Dict with session parameters for human-like behavior
    """
    return {
        "max_pages": random.randint(2, 5),
        "min_dwell_seconds": random.uniform(5, 12),
        "max_dwell_seconds": random.uniform(20, 45),
        "scroll_chunks": random.randint(2, 6),
        "mouse_movements_per_page": random.randint(1, 4),
        "break_probability": random.uniform(0.02, 0.08),
        "break_duration_range": (30, 120),
    }


def get_realistic_break_duration(pages_visited: int) -> float:
    """Return a human-realistic break duration based on session fatigue.

    After more pages, breaks tend to be longer (fatigue).

    Args:
        pages_visited: Number of pages visited in this session

    Returns:
        Break duration in seconds
    """
    base_break = random.uniform(30, 60)

    # Fatigue factor: longer sessions = longer breaks
    fatigue_factor = 1 + (pages_visited * 0.1)

    # Add randomness
    jitter = random.uniform(0.8, 1.2)

    return base_break * fatigue_factor * jitter
