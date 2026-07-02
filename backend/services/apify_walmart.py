"""Apify Walmart pricing — Tier 1 search (Unfenced) + Tier 2 detail enrichment."""

from __future__ import annotations

import os
import re
from typing import Any, TypedDict

import httpx

APIFY_BASE = "https://api.apify.com/v2"
TIER1_ACTOR = "unfenced-group~walmart-scraper"
TIER2_ACTOR = "e-commerce~walmart-product-detail-scraper"

UNIT_WORDS = {
    "cup", "cups", "tbsp", "tsp", "oz", "lb", "lbs", "g", "kg", "ml", "l",
    "piece", "pieces", "slice", "slices", "clove", "cloves", "can", "cans",
    "package", "pkg", "large", "medium", "small", "fresh", "frozen", "dried",
    "chopped", "diced", "minced", "whole", "boneless", "skinless",
}


class PriceResult(TypedDict, total=False):
    price: float | None
    unit_price: str | None
    product_url: str | None
    source: str


def apify_configured() -> bool:
    return bool(os.getenv("APIFY_API_TOKEN", "").strip())


def ingredient_search_term(raw: str) -> str:
    words = raw.strip().split()
    keyword_words = [
        w.strip(",")
        for w in words
        if w and not w[0].isdigit() and w.lower().replace(",", "") not in UNIT_WORDS
    ]
    return " ".join(keyword_words[:3]) if keyword_words else raw[:30]


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _extract_price_info(item: dict) -> tuple[float | None, str | None, str | None]:
    """Return (price, unit_price_str, product_url) from a Walmart product record."""
    price_info = item.get("priceInfo") or {}
    if isinstance(price_info, dict):
        price = _parse_price(price_info.get("price") or price_info.get("priceDisplay"))
        unit = price_info.get("unitPrice")
        unit_str = str(unit).strip() if unit else None
    else:
        price = None
        unit_str = None

    if price is None:
        for key in ("price", "currentPrice", "salePrice", "regularPrice"):
            price = _parse_price(item.get(key))
            if price is not None:
                break

    url = (
        item.get("url")
        or item.get("productUrl")
        or item.get("canonicalUrl")
        or item.get("link")
    )
    if url and not str(url).startswith("http"):
        url = f"https://www.walmart.com{url}"

    return price, unit_str, str(url) if url else None


def _pick_best_product(items: list[dict], term: str) -> dict | None:
    if not items:
        return None

    term_lower = term.lower()
    scored: list[tuple[float, dict]] = []

    for item in items:
        name = str(item.get("name") or item.get("title") or "").lower()
        price, _, _ = _extract_price_info(item)
        if price is None or price <= 0:
            continue
        score = price
        if item.get("isSponsored"):
            score += 5.0
        if term_lower and term_lower not in name:
            score += 2.0
        scored.append((score, item))

    if not scored:
        return None
    scored.sort(key=lambda x: x[0])
    return scored[0][1]


async def _run_actor(actor_id: str, actor_input: dict, timeout: float = 120.0) -> list[dict]:
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        return []

    url = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                params={"token": token},
                json=actor_input,
                timeout=timeout,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


async def _tier1_single(term: str, zip_code: str, max_results: int = 3) -> list[dict]:
    return await _run_actor(
        TIER1_ACTOR,
        {
            "mode": "search",
            "keywords": [term],
            "zipCode": zip_code,
            "maxResults": max_results,
            "fetchDetails": False,
        },
    )


def _group_by_keyword(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        kw = (
            item.get("searchKeyword")
            or item.get("keyword")
            or item.get("searchTerm")
            or item.get("query")
        )
        if kw:
            key = str(kw).lower().strip()
            grouped.setdefault(key, []).append(item)
    return grouped


async def search_ingredient_prices(
    items: list[tuple[str, str]],
    zip_code: str,
) -> dict[str, PriceResult]:
    """
    Tier 1 pricing for (raw_ingredient, search_term) pairs.
    Returns dict keyed by raw ingredient string.
    """
    if not apify_configured() or not zip_code or not items:
        return {}

    results: dict[str, PriceResult] = {}
    term_to_raws: dict[str, list[str]] = {}
    for raw, term in items:
        term_to_raws.setdefault(term.lower(), []).append(raw)

    unique_terms = list({term for _, term in items})
    batch_items = await _run_actor(
        TIER1_ACTOR,
        {
            "mode": "search",
            "keywords": unique_terms,
            "zipCode": zip_code,
            "maxResults": 3,
            "fetchDetails": False,
        },
    )

    grouped = _group_by_keyword(batch_items)
    unmapped_terms = set(unique_terms)

    for term in unique_terms:
        term_key = term.lower()
        products = grouped.get(term_key, [])
        if products:
            unmapped_terms.discard(term)
            best = _pick_best_product(products, term)
            if best:
                price, unit_price, url = _extract_price_info(best)
                for raw in term_to_raws.get(term_key, []):
                    results[raw] = {
                        "price": price,
                        "unit_price": unit_price,
                        "product_url": url,
                        "source": "walmart",
                    }

    for term in unmapped_terms:
        products = await _tier1_single(term, zip_code)
        best = _pick_best_product(products, term)
        if not best:
            continue
        price, unit_price, url = _extract_price_info(best)
        term_key = term.lower()
        for raw in term_to_raws.get(term_key, []):
            results[raw] = {
                "price": price,
                "unit_price": unit_price,
                "product_url": url,
                "source": "walmart",
            }

    return results


async def enrich_product_prices(
    url_to_raw: dict[str, str],
) -> dict[str, PriceResult]:
    """Tier 2 detail enrichment keyed by raw ingredient."""
    if not apify_configured() or not url_to_raw:
        return {}

    start_urls = [{"url": url} for url in url_to_raw]
    items = await _run_actor(
        TIER2_ACTOR,
        {
            "startUrls": start_urls,
            "maxProductsPerStartUrl": 1,
            "enqueueProductVariants": False,
        },
        timeout=180.0,
    )

    results: dict[str, PriceResult] = {}
    for item in items:
        _, unit_str, url = _extract_price_info(item)
        price_info = item.get("priceInfo") or {}
        if isinstance(price_info, dict) and not unit_str:
            unit_str = price_info.get("unitPrice")
            if unit_str:
                unit_str = str(unit_str).strip()

        price = _parse_price(price_info.get("price") if isinstance(price_info, dict) else None)
        if price is None:
            price, _, _ = _extract_price_info(item)

        item_url = item.get("url") or url
        if not item_url:
            continue

        raw = url_to_raw.get(str(item_url))
        if raw is None:
            for src_url, raw_name in url_to_raw.items():
                if src_url.rstrip("/") in str(item_url) or str(item_url).rstrip("/") in src_url:
                    raw = raw_name
                    break
        if raw is None:
            continue

        results[raw] = {
            "price": price,
            "unit_price": unit_str,
            "product_url": str(item_url),
            "source": "walmart_detail",
        }

    return results
