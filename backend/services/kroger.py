"""
Kroger Developer API client.
Docs: https://developer.kroger.com/api-products/api/product-api/v1/overview

Requires three env vars:
  KROGER_CLIENT_ID
  KROGER_CLIENT_SECRET
  KROGER_LOCATION_ID   (find via GET /v1/locations?filter.zipCode=XXXXX)
"""

import os
import time
from typing import Optional

import httpx

BASE = "https://api.kroger.com/v1"

# Simple in-process token cache
_token_cache: dict = {"access_token": None, "expires_at": 0.0}


def _creds() -> tuple[str, str]:
    client_id = os.getenv("KROGER_CLIENT_ID", "")
    client_secret = os.getenv("KROGER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError("KROGER_CLIENT_ID and KROGER_CLIENT_SECRET must be set")
    return client_id, client_secret


def _location_id() -> str:
    loc = os.getenv("KROGER_LOCATION_ID", "")
    if not loc:
        raise RuntimeError("KROGER_LOCATION_ID must be set")
    return loc


def kroger_configured() -> bool:
    return bool(
        os.getenv("KROGER_CLIENT_ID")
        and os.getenv("KROGER_CLIENT_SECRET")
        and os.getenv("KROGER_LOCATION_ID")
    )


async def _get_token() -> str:
    """Fetch and cache a client-credentials access token."""
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]  # type: ignore[return-value]

    client_id, client_secret = _creds()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/connect/oauth2/token",
            data={"grant_type": "client_credentials", "scope": "product.compact"},
            auth=(client_id, client_secret),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 1800) - 60
    return _token_cache["access_token"]  # type: ignore[return-value]


async def search_product_price(term: str, location_id: Optional[str] = None) -> Optional[float]:
    """
    Return the lowest price (USD) found for a product matching `term`
    at the given Kroger store location. Returns None if not found.
    """
    loc = location_id or _location_id()
    token = await _get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE}/products",
            params={
                "filter.term": term,
                "filter.locationId": loc,
                "filter.limit": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()

    items = data.get("data", [])
    prices: list[float] = []
    for item in items:
        for size in item.get("items", []):
            price_info = size.get("price", {})
            regular = price_info.get("regular")
            if regular is not None:
                prices.append(float(regular))
    return min(prices) if prices else None


async def estimate_ingredient_costs(
    ingredients: list[str],
    location_id: Optional[str] = None,
) -> dict[str, Optional[float]]:
    """
    Return a dict mapping each ingredient string to its estimated Kroger price.
    Uses only the first 1–2 words of each ingredient as the search term to
    reduce noise (e.g. "2 cups diced onion" → "onion").
    """
    results: dict[str, Optional[float]] = {}
    for raw in ingredients:
        # Strip quantities/units: take last meaningful word(s)
        words = raw.strip().split()
        # Remove leading numbers/fractions and common unit words
        unit_words = {
            "cup", "cups", "tbsp", "tsp", "oz", "lb", "lbs", "g", "kg",
            "ml", "l", "piece", "pieces", "slice", "slices", "clove", "cloves",
            "can", "cans", "package", "pkg", "large", "medium", "small",
            "fresh", "frozen", "dried", "chopped", "diced", "minced",
        }
        keyword_words = [
            w for w in words
            if not w[0].isdigit() and w.lower().replace(",", "") not in unit_words
        ]
        term = " ".join(keyword_words[:2]) if keyword_words else raw[:20]
        try:
            price = await search_product_price(term, location_id)
        except Exception:
            price = None
        results[raw] = price
    return results


async def estimate_recipe_cost(
    ingredients: list[str],
    location_id: Optional[str] = None,
) -> Optional[float]:
    """Return total estimated cost for all ingredients in a recipe, or None."""
    costs = await estimate_ingredient_costs(ingredients, location_id)
    known = [v for v in costs.values() if v is not None]
    return round(sum(known), 2) if known else None
