import re
from typing import Optional


def parse_sold_price(price_text: str) -> Optional[float]:
    """
    Parse sold price from text like '$1,500,000', '$2.1M', etc.
    """
    if not price_text:
        return None

    # Clean string
    price_text = price_text.lower().replace(",", "").replace("$", "").strip()

    # Handle 'm' (millions)
    if "m" in price_text:
        match = re.search(r"([\d.]+)", price_text)
        if match:
            return float(match.group(1)) * 1_000_000

    # Handle pure numbers
    match = re.search(r"(\d{5,})", price_text)
    if match:
        return float(match.group(1))

    return None
