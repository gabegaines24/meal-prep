"""Pricing orchestrator with AP-style cache (Apify Walmart + USDA fallback)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.models.models import PriceCache, UserProfile
from backend.services import apify_walmart, usda

WALMART_TTL = timedelta(hours=24)
USDA_TTL = timedelta(days=30)
MEALS_PER_WEEK = 21
WALMART_SOURCES = ("walmart", "walmart_detail")


def get_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
    if not profile:
        profile = UserProfile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def get_per_meal_budget(profile: UserProfile | None) -> float | None:
    if not profile or not profile.weekly_budget or profile.weekly_budget <= 0:
        return None
    return profile.weekly_budget / MEALS_PER_WEEK


def spoonacular_max_price_cents(profile: UserProfile | None) -> int | None:
    per_meal = get_per_meal_budget(profile)
    if per_meal is None:
        return None
    return int(per_meal * 100)


def _normalize_key(raw: str) -> str:
    return raw.lower().strip()


def _zip_scope(profile: UserProfile | None) -> str | None:
    if not profile or not profile.zip_code:
        return None
    return profile.zip_code.strip()


def _cache_fresh(entry: PriceCache, source: str) -> bool:
    if source in WALMART_SOURCES:
        ttl = WALMART_TTL
    elif source == "usda":
        ttl = USDA_TTL
    else:
        return False
    if not entry.fetched_at:
        return False
    return datetime.utcnow() - entry.fetched_at < ttl


def _get_cached_walmart(db: Session, key: str, zip_code: str | None) -> PriceCache | None:
    if not zip_code:
        return None
    for source in WALMART_SOURCES:
        entry = (
            db.query(PriceCache)
            .filter(
                PriceCache.ingredient_key == key,
                PriceCache.source == source,
                PriceCache.location_id == zip_code,
            )
            .order_by(PriceCache.fetched_at.desc())
            .first()
        )
        if entry and _cache_fresh(entry, source):
            return entry
    return None


def _get_cached_usda(db: Session, key: str) -> PriceCache | None:
    entry = (
        db.query(PriceCache)
        .filter(
            PriceCache.ingredient_key == key,
            PriceCache.source == "usda",
            PriceCache.location_id.is_(None),
        )
        .order_by(PriceCache.fetched_at.desc())
        .first()
    )
    if entry and _cache_fresh(entry, "usda"):
        return entry
    return None


def _get_stale_cached(db: Session, key: str, zip_code: str | None) -> PriceCache | None:
    best: PriceCache | None = None
    sources = list(WALMART_SOURCES) + ["usda"]
    for source in sources:
        q = db.query(PriceCache).filter(
            PriceCache.ingredient_key == key,
            PriceCache.source == source,
        )
        if source in WALMART_SOURCES:
            if not zip_code:
                continue
            q = q.filter(PriceCache.location_id == zip_code)
        else:
            q = q.filter(PriceCache.location_id.is_(None))
        entry = q.order_by(PriceCache.fetched_at.desc()).first()
        if entry and (best is None or (entry.fetched_at and best.fetched_at and entry.fetched_at > best.fetched_at)):
            best = entry
    return best


def _write_cache(
    db: Session,
    key: str,
    price: float,
    source: str,
    location_id: str | None,
    unit: str | None = None,
) -> PriceCache:
    loc = location_id if source in WALMART_SOURCES else None
    entry = PriceCache(
        ingredient_key=key,
        location_id=loc,
        price=price,
        unit=unit,
        source=source,
        fetched_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _result_from_cache(raw: str, entry: PriceCache, stale: bool = False) -> dict[str, Any]:
    return {
        "ingredient": raw,
        "price": entry.price,
        "source": entry.source,
        "stale": stale,
        "fetched_at": entry.fetched_at.isoformat() if entry.fetched_at else None,
    }


def _result_unknown(raw: str) -> dict[str, Any]:
    return {
        "ingredient": raw,
        "price": None,
        "source": "unknown",
        "stale": False,
        "fetched_at": None,
    }


async def price_ingredients(
    ingredients: list[str],
    profile: UserProfile | None,
    db: Session,
) -> dict[str, Any]:
    zip_code = _zip_scope(profile)
    priced: dict[str, dict[str, Any]] = {}
    misses: list[str] = []

    for raw in ingredients:
        key = _normalize_key(raw)
        cached = _get_cached_walmart(db, key, zip_code)
        if cached:
            priced[raw] = _result_from_cache(raw, cached)
            continue

        cached_usda = _get_cached_usda(db, key)
        if cached_usda:
            priced[raw] = _result_from_cache(raw, cached_usda)
            continue

        misses.append(raw)

    if misses and apify_walmart.apify_configured() and zip_code:
        term_pairs = [(raw, apify_walmart.ingredient_search_term(raw)) for raw in misses]
        try:
            tier1 = await apify_walmart.search_ingredient_prices(term_pairs, zip_code)
        except Exception:
            tier1 = {}

        tier2_urls: dict[str, str] = {}
        still_missing: list[str] = []

        for raw in misses:
            hit = tier1.get(raw)
            if not hit:
                still_missing.append(raw)
                continue

            price = hit.get("price")
            unit_price = hit.get("unit_price")
            product_url = hit.get("product_url")

            if price is not None and price > 0:
                entry = _write_cache(
                    db, _normalize_key(raw), price, "walmart", zip_code, unit=unit_price
                )
                priced[raw] = _result_from_cache(raw, entry)
            elif product_url:
                tier2_urls[product_url] = raw
                still_missing.append(raw)
            else:
                still_missing.append(raw)

        if tier2_urls:
            try:
                tier2 = await apify_walmart.enrich_product_prices(tier2_urls)
            except Exception:
                tier2 = {}

            for raw in list(still_missing):
                hit = tier2.get(raw)
                if not hit or hit.get("price") is None:
                    continue
                entry = _write_cache(
                    db,
                    _normalize_key(raw),
                    hit["price"],
                    "walmart_detail",
                    zip_code,
                    unit=hit.get("unit_price"),
                )
                priced[raw] = _result_from_cache(raw, entry)
                still_missing.remove(raw)

        misses = still_missing

    for raw in misses:
        if raw in priced:
            continue
        key = _normalize_key(raw)

        usda_price = usda.lookup_commodity_price(key)
        if usda_price is not None:
            entry = _write_cache(db, key, usda_price, "usda", None)
            priced[raw] = _result_from_cache(raw, entry)
            continue

        stale_entry = _get_stale_cached(db, key, zip_code)
        if stale_entry:
            priced[raw] = _result_from_cache(raw, stale_entry, stale=True)
        else:
            priced[raw] = _result_unknown(raw)

    total = 0.0
    known = 0
    stale_any = False
    latest_fetched: datetime | None = None
    source_breakdown: dict[str, int] = {
        "walmart": 0,
        "walmart_detail": 0,
        "usda": 0,
        "unknown": 0,
    }

    for raw in ingredients:
        result = priced.get(raw, _result_unknown(raw))
        if result["price"] is not None:
            total += result["price"]
            known += 1
            src = result.get("source", "unknown")
            source_breakdown[src] = source_breakdown.get(src, 0) + 1
        if result.get("stale"):
            stale_any = True
        if result.get("fetched_at"):
            dt = datetime.fromisoformat(result["fetched_at"])
            if latest_fetched is None or dt > latest_fetched:
                latest_fetched = dt

    return {
        "prices": priced,
        "total": round(total, 2),
        "known_count": known,
        "stale": stale_any,
        "fetched_at": latest_fetched.isoformat() if latest_fetched else None,
        "source_breakdown": source_breakdown,
    }


def _dedup_ingredient_names(slots: list) -> list[str]:
    import json

    seen: set[str] = set()
    names: list[str] = []
    for slot in slots:
        if not slot.recipe or not slot.recipe.ingredients_json:
            continue
        try:
            for ing in json.loads(slot.recipe.ingredients_json):
                key = ing.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    names.append(ing.strip())
        except json.JSONDecodeError:
            continue
    return names


async def price_week(slots: list, profile: UserProfile | None, db: Session) -> dict[str, Any]:
    ingredients = _dedup_ingredient_names(slots)
    zip_code = _zip_scope(profile) or ""
    budget = profile.weekly_budget if profile and profile.weekly_budget else 0.0

    if not ingredients:
        return {
            "budget": budget or 0.0,
            "estimated_total": 0.0,
            "remaining": budget or 0.0,
            "over_budget": False,
            "prices_as_of": None,
            "stale": False,
            "store_name": "Walmart" if zip_code else "",
            "zip_code": zip_code,
            "ingredient_pricing": {"prices": {}, "total": 0.0},
        }

    pricing = await price_ingredients(ingredients, profile, db)
    total = pricing["total"]
    remaining = round(budget - total, 2) if budget else 0.0

    return {
        "budget": budget,
        "estimated_total": total,
        "remaining": remaining,
        "over_budget": budget > 0 and total > budget,
        "prices_as_of": pricing.get("fetched_at"),
        "stale": pricing.get("stale", False),
        "source_breakdown": pricing.get("source_breakdown", {}),
        "store_name": "Walmart" if zip_code else "",
        "zip_code": zip_code,
        "ingredient_pricing": pricing,
    }


def recipe_cost_per_serving(recipe) -> float | None:
    if recipe.estimated_cost_per_serving is not None:
        return recipe.estimated_cost_per_serving
    return None
