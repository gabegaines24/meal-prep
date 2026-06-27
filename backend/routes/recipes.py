import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Recipe
from backend.services import spoonacular

router = APIRouter()


class RecipeOut(BaseModel):
    id: int
    spoonacular_id: Optional[int] = None
    title: str
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    ingredients: list[str] = []
    favorited: bool = False

    model_config = {"from_attributes": True}


def _to_out(recipe: Recipe) -> RecipeOut:
    ingredients = []
    if recipe.ingredients_json:
        try:
            ingredients = json.loads(recipe.ingredients_json)
        except json.JSONDecodeError:
            pass
    return RecipeOut(
        id=recipe.id,
        spoonacular_id=recipe.spoonacular_id,
        title=recipe.title,
        image_url=recipe.image_url,
        source_url=recipe.source_url,
        calories=recipe.calories,
        protein=recipe.protein,
        carbs=recipe.carbs,
        fat=recipe.fat,
        ingredients=ingredients,
        favorited=recipe.favorited,
    )


def _upsert_recipe(db: Session, data: dict) -> Recipe:
    """Insert or update a recipe row from a Spoonacular data dict."""
    existing = (
        db.query(Recipe)
        .filter(Recipe.spoonacular_id == data["spoonacular_id"])
        .first()
    )
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    recipe = Recipe(**data)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.get("/search", response_model=list[RecipeOut])
async def search_recipes(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    results = await spoonacular.search_recipes(query)
    return [_to_out(_upsert_recipe(db, r)) for r in results]


@router.get("/favorites", response_model=list[RecipeOut])
def get_favorites(db: Session = Depends(get_db)):
    recipes = db.query(Recipe).filter(Recipe.favorited == True).all()
    return [_to_out(r) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe:
        return _to_out(recipe)

    # Not in cache — fetch from Spoonacular using recipe_id as spoonacular_id
    try:
        data = await spoonacular.get_recipe_by_id(recipe_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _to_out(_upsert_recipe(db, data))


@router.post("/{recipe_id}/favorite", response_model=RecipeOut)
def toggle_favorite(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.favorited = not recipe.favorited
    db.commit()
    db.refresh(recipe)
    return _to_out(recipe)
