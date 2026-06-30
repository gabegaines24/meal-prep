from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import claude, spoonacular
from backend.routes.recipes import RecipeOut, _upsert_recipe
from backend.routes.chat import ChatContext, ChatRequest, chat as chat_handler

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ScanResult(BaseModel):
    ingredients: list[str]
    recipes: list[RecipeOut]
    agent_prompt: str | None = None


def _agent_prompt(ingredients: list[str]) -> str:
    joined = ", ".join(ingredients)
    return (
        f"I scanned my fridge and found these ingredients: {joined}. "
        "Please plan dinners for any empty dinner slots this week using what's available, "
        "and tell me what you assigned."
    )


async def _scan_image(file: UploadFile) -> list[str]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{file.content_type}'. Use JPEG, PNG, WEBP, or GIF.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 20 MB.")

    try:
        return await claude.detect_ingredients(image_bytes, file.content_type or "image/jpeg")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("", response_model=ScanResult)
async def scan_fridge(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ingredients = await _scan_image(file)

    if not ingredients:
        return ScanResult(ingredients=[], recipes=[], agent_prompt=None)

    try:
        recipe_data = await spoonacular.search_by_ingredients(ingredients)
    except Exception:
        recipe_data = []

    recipes = [
        RecipeOut(**{**_upsert_recipe(db, r).__dict__, "ingredients": []})
        for r in recipe_data
    ]

    return ScanResult(
        ingredients=ingredients,
        recipes=recipes,
        agent_prompt=_agent_prompt(ingredients),
    )


@router.post("/plan")
async def scan_and_plan(
    file: UploadFile = File(...),
    session_id: str = "scanner",
    db: Session = Depends(get_db),
):
    """Scan a fridge photo and stream an agent meal plan (SSE)."""
    ingredients = await _scan_image(file)
    if not ingredients:
        raise HTTPException(status_code=422, detail="No ingredients detected in the image.")

    request = ChatRequest(
        session_id=session_id,
        message=_agent_prompt(ingredients),
        context=ChatContext(scan_ingredients=ingredients),
    )
    return await chat_handler(request, db)
