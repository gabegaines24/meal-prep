import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MealPlan, UserProfile
from backend.services import file_gen, kroger, resend as resend_svc

router = APIRouter()


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _compute_weekly_macros(slots: list[MealPlan]) -> dict:
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for slot in slots:
        if slot.recipe:
            totals["calories"] += slot.recipe.calories or 0
            totals["protein"] += slot.recipe.protein or 0
            totals["carbs"] += slot.recipe.carbs or 0
            totals["fat"] += slot.recipe.fat or 0
    return totals


@router.post("/send")
async def send_digest(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    start = _monday(week_start or date.today())
    slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()

    if not slots:
        raise HTTPException(
            status_code=404,
            detail=f"No meal plan found for week starting {start}.",
        )

    weekly_macros = _compute_weekly_macros(slots)

    # Build file attachments
    profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
    store_name = profile.store_name if profile else ""
    weekly_budget = profile.weekly_budget if profile else 0.0
    location_id = profile.kroger_location_id if profile else ""

    # Gather unique ingredients for Kroger pricing
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

    prices: dict = {}
    if kroger.kroger_configured() and all_ingredients and location_id:
        try:
            prices = await kroger.estimate_ingredient_costs(all_ingredients, location_id)
        except Exception:
            prices = {}

    grocery_html = file_gen.grocery_list_html(
        week_start=start,
        slots=slots,
        store_name=store_name,
        weekly_budget=weekly_budget,
        ingredient_prices=prices,
    )
    recipe_html = file_gen.recipe_book_html(week_start=start, slots=slots)

    try:
        result = resend_svc.send_digest(
            start, slots, weekly_macros,
            grocery_list_html=grocery_html,
            recipe_book_html=recipe_html,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"status": "sent", "week_start": str(start), "resend_id": result.get("id")}
