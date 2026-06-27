from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import claude, spoonacular
from backend.routes.recipes import RecipeOut, _upsert_recipe

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ScanResult(BaseModel):
    ingredients: list[str]
    recipes: list[RecipeOut]


@router.post("", response_model=ScanResult)
async def scan_fridge(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{file.content_type}'. Use JPEG, PNG, WEBP, or GIF.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:  # 20 MB guard
        raise HTTPException(status_code=413, detail="Image must be smaller than 20 MB.")

    try:
        ingredients = await claude.detect_ingredients(image_bytes, file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not ingredients:
        return ScanResult(ingredients=[], recipes=[])

    try:
        recipe_data = await spoonacular.search_by_ingredients(ingredients)
    except Exception:
        recipe_data = []

    recipes = [RecipeOut(**{**_upsert_recipe(db, r).__dict__, "ingredients": []}) for r in recipe_data]

    return ScanResult(ingredients=ingredients, recipes=recipes)
