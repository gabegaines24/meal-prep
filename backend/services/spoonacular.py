import json
import os
from typing import Any

import httpx

BASE_URL = "https://api.spoonacular.com"


def _api_key() -> str:
    key = os.getenv("SPOONACULAR_API_KEY", "")
    if not key:
        raise RuntimeError("SPOONACULAR_API_KEY is not set")
    return key


def _params(**kwargs: Any) -> dict:
    return {"apiKey": _api_key(), **kwargs}


async def search_recipes(query: str, number: int = 12) -> list[dict]:
    """Search recipes by keyword. Returns a list of summary dicts."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/recipes/complexSearch",
            params=_params(
                query=query,
                number=number,
                addRecipeNutrition=True,
                instructionsRequired=True,
            ),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    return [_normalise(r) for r in data.get("results", [])]


async def get_recipe_by_id(spoonacular_id: int) -> dict:
    """Fetch full recipe details including nutrition."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/recipes/{spoonacular_id}/information",
            params=_params(includeNutrition=True),
            timeout=15,
        )
        resp.raise_for_status()
    return _normalise(resp.json())


async def search_by_ingredients(ingredients: list[str], number: int = 10) -> list[dict]:
    """Find recipes that use the supplied ingredients."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/recipes/findByIngredients",
            params=_params(
                ingredients=",".join(ingredients),
                number=number,
                ranking=1,
                ignorePantry=True,
            ),
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()

    # findByIngredients doesn't include nutrition — enrich with bulk endpoint
    if not results:
        return []
    ids = [str(r["id"]) for r in results]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/recipes/informationBulk",
            params=_params(ids=",".join(ids), includeNutrition=True),
            timeout=20,
        )
        resp.raise_for_status()
        enriched = resp.json()
    return [_normalise(r) for r in enriched]


def _normalise(raw: dict) -> dict:
    """Flatten a Spoonacular recipe dict into our standard shape."""
    nutrition = raw.get("nutrition", {})
    nutrients = {n["name"].lower(): n["amount"] for n in nutrition.get("nutrients", [])}

    ingredients = [
        i.get("original", i.get("name", ""))
        for i in raw.get("extendedIngredients", [])
    ]

    return {
        "spoonacular_id": raw.get("id"),
        "title": raw.get("title", ""),
        "image_url": raw.get("image", ""),
        "source_url": raw.get("sourceUrl", ""),
        "calories": nutrients.get("calories"),
        "protein": nutrients.get("protein"),
        "carbs": nutrients.get("carbohydrates"),
        "fat": nutrients.get("fat"),
        "ingredients_json": json.dumps(ingredients),
    }
