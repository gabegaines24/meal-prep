"""Build structured grocery lists from meal plan slots."""

import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.models.models import UserProfile
from backend.services import pricing as pricing_svc

CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "Produce",
        [
            "lettuce", "spinach", "tomato", "onion", "garlic", "pepper", "carrot",
            "celery", "broccoli", "potato", "avocado", "lemon", "lime", "apple",
            "banana", "mushroom", "cucumber", "zucchini", "kale", "cilantro",
            "parsley", "basil", "ginger", "scallion", "shallot",
        ],
    ),
    (
        "Protein",
        [
            "chicken", "beef", "pork", "fish", "salmon", "shrimp", "tuna", "turkey",
            "bacon", "sausage", "steak", "egg", "tofu", "tempeh", "lamb", "cod",
        ],
    ),
    (
        "Dairy",
        ["milk", "cheese", "butter", "yogurt", "cream", "parmesan", "mozzarella", "feta"],
    ),
    (
        "Pantry",
        [
            "flour", "sugar", "rice", "pasta", "oil", "vinegar", "sauce", "broth",
            "stock", "bean", "lentil", "honey", "cumin", "oregano", "paprika",
            "soy sauce", "mustard", "mayonnaise",
        ],
    ),
    ("Bakery", ["bread", "tortilla", "bun", "roll", "pita"]),
    ("Frozen", ["frozen"]),
]

CATEGORY_ORDER = ["Produce", "Protein", "Dairy", "Bakery", "Pantry", "Frozen", "Other"]


def categorize(ingredient: str) -> str:
    lower = ingredient.lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return category
    return "Other"


def _aggregate_ingredients(slots: list) -> tuple[list[str], dict[str, set[str]], dict[str, str]]:
    ingredient_map: dict[str, set[str]] = {}
    display_names: dict[str, str] = {}

    for slot in slots:
        if not slot.recipe or not slot.recipe.ingredients_json:
            continue
        recipe_title = slot.recipe.title
        try:
            ingredients = json.loads(slot.recipe.ingredients_json)
        except json.JSONDecodeError:
            continue
        for ing in ingredients:
            key = ing.lower().strip()
            if not key:
                continue
            if key not in ingredient_map:
                ingredient_map[key] = set()
                display_names[key] = ing.strip()
            ingredient_map[key].add(recipe_title)

    names = [
        display_names[key]
        for key in sorted(ingredient_map.keys(), key=lambda k: display_names[k].lower())
    ]
    return names, ingredient_map, display_names


async def build_grocery_list(
    week_start: date,
    slots: list,
    profile: UserProfile | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    names, ingredient_map, display_names = _aggregate_ingredients(slots)

    pricing_result: dict[str, Any] = {
        "prices": {},
        "total": 0.0,
        "stale": False,
        "fetched_at": None,
    }
    if db is not None and names:
        pricing_result = await pricing_svc.price_ingredients(names, profile, db)

    items = []
    category_totals: dict[str, float] = {cat: 0.0 for cat in CATEGORY_ORDER}

    for key in sorted(ingredient_map.keys(), key=lambda k: display_names[k].lower()):
        name = display_names[key]
        price_info = pricing_result["prices"].get(name, {})
        price = price_info.get("price")
        category = categorize(name)
        if price is not None:
            category_totals[category] = category_totals.get(category, 0.0) + price
        items.append(
            {
                "name": name,
                "recipes": sorted(ingredient_map[key]),
                "category": category,
                "price": price,
                "price_source": price_info.get("source"),
                "stale": price_info.get("stale", False),
            }
        )

    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        by_category[item["category"]].append(item)

    categories = [
        {
            "name": cat,
            "items": by_category[cat],
            "subtotal": round(category_totals.get(cat, 0.0), 2) if category_totals.get(cat) else None,
        }
        for cat in CATEGORY_ORDER
        if by_category[cat]
    ]

    budget = profile.weekly_budget if profile and profile.weekly_budget else 0.0
    zip_code = (profile.zip_code or "").strip() if profile else ""
    total = pricing_result.get("total", 0.0)

    return {
        "week_start_date": str(week_start),
        "items": items,
        "categories": categories,
        "budget_summary": {
            "budget": budget,
            "estimated_total": total,
            "remaining": round(budget - total, 2) if budget else 0.0,
            "over_budget": budget > 0 and total > budget,
            "prices_as_of": pricing_result.get("fetched_at"),
            "stale": pricing_result.get("stale", False),
            "store_name": "Walmart" if zip_code else "",
            "zip_code": zip_code,
        },
    }
