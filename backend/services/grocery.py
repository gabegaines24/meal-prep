"""Build structured grocery lists from meal plan slots."""

import json
from datetime import date

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


def build_grocery_list(week_start: date, slots: list) -> dict:
    """
    Aggregate ingredients across the week's recipes.

    Returns:
        {
            "week_start_date": "YYYY-MM-DD",
            "items": [{"name": str, "recipes": [str], "category": str}],
            "categories": [{"name": str, "items": [...]}],
        }
    """
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

    items = [
        {
            "name": display_names[key],
            "recipes": sorted(recipe_titles),
            "category": categorize(display_names[key]),
        }
        for key, recipe_titles in sorted(ingredient_map.items(), key=lambda x: display_names[x[0]].lower())
    ]

    by_category: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        by_category[item["category"]].append(item)

    categories = [
        {"name": cat, "items": by_category[cat]}
        for cat in CATEGORY_ORDER
        if by_category[cat]
    ]

    return {
        "week_start_date": str(week_start),
        "items": items,
        "categories": categories,
    }
