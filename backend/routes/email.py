from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MealPlan
from backend.services import resend as resend_svc

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
def send_digest(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    start = _monday(week_start or date.today())
    slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()

    if not slots:
        raise HTTPException(
            status_code=404,
            detail=f"No meal plan found for week starting {start}.",
        )

    weekly_macros = _compute_weekly_macros(slots)

    try:
        result = resend_svc.send_digest(start, slots, weekly_macros)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"status": "sent", "week_start": str(start), "resend_id": result.get("id")}
