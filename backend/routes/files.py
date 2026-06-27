import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MealPlan, UserProfile
from backend.services import file_gen, kroger

router = APIRouter()


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _get_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
    if not profile:
        profile = UserProfile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _get_slots(db: Session, start: date) -> list[MealPlan]:
    return db.query(MealPlan).filter(MealPlan.week_start_date == start).all()


@router.get("/grocery-list", response_class=HTMLResponse)
async def get_grocery_list(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    if not slots:
        raise HTTPException(status_code=404, detail=f"No meal plan for week starting {start}.")

    profile = _get_profile(db)

    # Gather all ingredients across the week
    all_ingredients: list[str] = []
    seen: set[str] = set()
    for slot in slots:
        if slot.recipe and slot.recipe.ingredients_json:
            try:
                for ing in json.loads(slot.recipe.ingredients_json):
                    key = ing.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        all_ingredients.append(ing)
            except json.JSONDecodeError:
                pass

    # Optionally price ingredients via Kroger
    prices: dict = {}
    if kroger.kroger_configured() and all_ingredients and profile.kroger_location_id:
        try:
            prices = await kroger.estimate_ingredient_costs(
                all_ingredients, profile.kroger_location_id
            )
        except Exception:
            prices = {}

    html = file_gen.grocery_list_html(
        week_start=start,
        slots=slots,
        store_name=profile.store_name or "",
        weekly_budget=profile.weekly_budget or 0.0,
        ingredient_prices=prices,
    )
    headers = {"Content-Disposition": f'attachment; filename="grocery-list-{start}.html"'}
    return HTMLResponse(content=html, headers=headers)


@router.get("/recipe-book", response_class=HTMLResponse)
def get_recipe_book(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    if not slots:
        raise HTTPException(status_code=404, detail=f"No meal plan for week starting {start}.")

    html = file_gen.recipe_book_html(week_start=start, slots=slots)
    headers = {"Content-Disposition": f'attachment; filename="recipe-book-{start}.html"'}
    return HTMLResponse(content=html, headers=headers)
