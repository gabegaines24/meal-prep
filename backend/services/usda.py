"""USDA commodity price fallback (static bundled averages)."""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "usda_prices.json"
_prices: dict[str, float] | None = None


def _load_prices() -> dict[str, float]:
    global _prices
    if _prices is None:
        with open(_DATA_PATH) as f:
            _prices = {k.lower(): float(v) for k, v in json.load(f).items()}
    return _prices


def lookup_commodity_price(ingredient_key: str) -> float | None:
    """Return an estimated USD price for a normalized ingredient key."""
    key = ingredient_key.lower().strip()
    prices = _load_prices()
    if key in prices:
        return prices[key]

    for term, price in prices.items():
        if term in key or key in term:
            return price
    return None
