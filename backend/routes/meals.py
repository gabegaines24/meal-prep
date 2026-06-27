import random
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MacroGoals, MealPlan, MealType, Recipe

router = APIRouter()

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class RecipeSummary(BaseModel):
    id: int
    title: str
    image_url: Optional[str] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

    model_config = {"from_attributes": True}


class SlotOut(BaseModel):
    id: int
    week_start_date: date
    day_of_week: int
    meal_type: MealType
    recipe: Optional[RecipeSummary] = None

    model_config = {"from_attributes": True}


class SlotIn(BaseModel):
    recipe_id: int


class WeekOut(BaseModel):
    week_start_date: date
    slots: list[SlotOut]
    daily_macros: list[dict]  # one entry per day, keys: day, calories, protein, carbs, fat
    weekly_macros: dict


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _compute_macros(slots: list[MealPlan]) -> tuple[list[dict], dict]:
    daily: dict[int, dict] = {
        i: {"day": DAYS[i], "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
        for i in range(7)
    }
    for slot in slots:
        if slot.recipe:
            d = daily[slot.day_of_week]
            d["calories"] += slot.recipe.calories or 0
            d["protein"] += slot.recipe.protein or 0
            d["carbs"] += slot.recipe.carbs or 0
            d["fat"] += slot.recipe.fat or 0

    weekly = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    for d in daily.values():
        for key in weekly:
            weekly[key] += d[key]

    return list(daily.values()), weekly


@router.get("", response_model=WeekOut)
def get_week(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    start = _monday(week_start or date.today())
    slots = (
        db.query(MealPlan)
        .filter(MealPlan.week_start_date == start)
        .all()
    )
    daily, weekly = _compute_macros(slots)
    return WeekOut(week_start_date=start, slots=slots, daily_macros=daily, weekly_macros=weekly)


@router.put("/{day}/{meal_type}", response_model=SlotOut)
def assign_slot(
    day: int,
    meal_type: MealType,
    payload: SlotIn,
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    if day not in range(7):
        raise HTTPException(status_code=422, detail="day must be 0–6")
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    start = _monday(week_start or date.today())
    slot = (
        db.query(MealPlan)
        .filter(
            MealPlan.week_start_date == start,
            MealPlan.day_of_week == day,
            MealPlan.meal_type == meal_type,
        )
        .first()
    )
    if slot:
        slot.recipe_id = payload.recipe_id
    else:
        slot = MealPlan(
            week_start_date=start,
            day_of_week=day,
            meal_type=meal_type,
            recipe_id=payload.recipe_id,
        )
        db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.delete("/{day}/{meal_type}", status_code=204)
def clear_slot(
    day: int,
    meal_type: MealType,
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slot = (
        db.query(MealPlan)
        .filter(
            MealPlan.week_start_date == start,
            MealPlan.day_of_week == day,
            MealPlan.meal_type == meal_type,
        )
        .first()
    )
    if slot:
        db.delete(slot)
        db.commit()


@router.post("/autogenerate", response_model=WeekOut)
def autogenerate(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    """
    Fill the current week with randomly selected cached recipes.
    Only assigns slots that are currently empty.
    """
    start = _monday(week_start or date.today())
    recipes = db.query(Recipe).all()
    if not recipes:
        raise HTTPException(
            status_code=400,
            detail="No recipes in the database yet. Search for some recipes first.",
        )

    goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
    target_cal = goals.calories if goals else 2000

    # Aim to distribute calories roughly evenly across meals
    # breakfast ~25%, lunch ~35%, dinner ~40%
    targets = {
        MealType.breakfast: target_cal * 0.25,
        MealType.lunch: target_cal * 0.35,
        MealType.dinner: target_cal * 0.40,
    }

    for day in range(7):
        for meal_type in MealType:
            existing = (
                db.query(MealPlan)
                .filter(
                    MealPlan.week_start_date == start,
                    MealPlan.day_of_week == day,
                    MealPlan.meal_type == meal_type,
                )
                .first()
            )
            if existing:
                continue

            # Pick the recipe whose calorie count is closest to the meal target
            target = targets[meal_type]
            best = min(
                recipes,
                key=lambda r: abs((r.calories or 500) - target),
            )
            # Add a little variety by picking randomly from the 3 closest options
            candidates = sorted(recipes, key=lambda r: abs((r.calories or 500) - target))[:3]
            chosen = random.choice(candidates)

            slot = MealPlan(
                week_start_date=start,
                day_of_week=day,
                meal_type=meal_type,
                recipe_id=chosen.id,
            )
            db.add(slot)

    db.commit()

    slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
    daily, weekly = _compute_macros(slots)
    return WeekOut(week_start_date=start, slots=slots, daily_macros=daily, weekly_macros=weekly)
