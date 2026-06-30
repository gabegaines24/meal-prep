import random
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MacroGoals, MealPlan, MealType, Recipe
from backend.routes.recipes import _load_filters, _upsert_recipe
from backend.services import spoonacular

router = APIRouter()

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

MEAL_FRAC = {
    MealType.breakfast: 0.25,
    MealType.lunch: 0.35,
    MealType.dinner: 0.40,
}

MACRO_WEIGHTS = {"calories": 1.0, "protein": 2.0, "carbs": 1.0, "fat": 1.0}

SEED_QUERIES = [
    "healthy breakfast",
    "healthy lunch",
    "healthy dinner",
    "high protein",
    "chicken",
    "salad",
    "pasta",
]


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


class MacroGap(BaseModel):
    macro: str
    actual: float
    target: float
    gap: float


class WeekOut(BaseModel):
    week_start_date: date
    slots: list[SlotOut]
    daily_macros: list[dict]
    weekly_macros: dict
    macro_gaps: list[MacroGap] = []


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _macro_value(recipe: Recipe, key: str) -> float:
    return getattr(recipe, key) or 0.0


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


def _compute_macro_gaps(weekly: dict, goals: MacroGoals) -> list[MacroGap]:
    gaps: list[MacroGap] = []
    weekly_targets = {
        "calories": goals.calories * 7,
        "protein": goals.protein * 7,
        "carbs": goals.carbs * 7,
        "fat": goals.fat * 7,
    }
    for key, target in weekly_targets.items():
        actual = weekly[key]
        gap = target - actual
        if abs(gap) >= 1:
            gaps.append(MacroGap(macro=key, actual=actual, target=target, gap=gap))
    return gaps


def _meal_targets(goals: MacroGoals, meal_type: MealType) -> dict[str, float]:
    frac = MEAL_FRAC[meal_type]
    return {
        "calories": goals.calories * frac,
        "protein": goals.protein * frac,
        "carbs": goals.carbs * frac,
        "fat": goals.fat * frac,
    }


def _score_recipe(
    recipe: Recipe,
    meal_target: dict[str, float],
    day_remaining: dict[str, float],
    week_remaining: dict[str, float],
) -> float:
    """Lower is better."""
    score = 0.0
    for key, weight in MACRO_WEIGHTS.items():
        value = _macro_value(recipe, key)
        meal_goal = max(meal_target[key], 1.0)
        score += weight * abs(value - meal_target[key]) / meal_goal

        if day_remaining[key] > 0:
            score += 0.3 * weight * abs(value - day_remaining[key]) / max(day_remaining[key], 1.0)
        if week_remaining[key] > 0:
            score += 0.15 * weight * abs(value - week_remaining[key]) / max(week_remaining[key], 1.0)

    if recipe.favorited:
        score *= 0.65
    return score


async def _ensure_recipe_details(db: Session, recipe: Recipe) -> Recipe:
    if recipe.ingredients_json and recipe.calories is not None:
        return recipe
    if not recipe.spoonacular_id:
        return recipe
    data = await spoonacular.get_recipe_by_id(recipe.spoonacular_id)
    data["favorited"] = recipe.favorited
    return _upsert_recipe(db, data)


async def _seed_recipe_pool(db: Session, diet: str, allergens: list[str]) -> list[Recipe]:
    favorites = db.query(Recipe).filter(Recipe.favorited == True).all()
    all_recipes = db.query(Recipe).all()

    if len(all_recipes) >= 15 and favorites:
        return favorites

    for query in SEED_QUERIES:
        results = await spoonacular.search_recipes(
            query, number=6, diet=diet, intolerances=allergens
        )
        for data in results:
            _upsert_recipe(db, data)

    favorites = db.query(Recipe).filter(Recipe.favorited == True).all()
    if favorites:
        return favorites
    return db.query(Recipe).all()


@router.get("", response_model=WeekOut)
def get_week(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    start = _monday(week_start or date.today())
    slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
    daily, weekly = _compute_macros(slots)
    goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
    gaps = _compute_macro_gaps(weekly, goals) if goals else []
    return WeekOut(
        week_start_date=start,
        slots=slots,
        daily_macros=daily,
        weekly_macros=weekly,
        macro_gaps=gaps,
    )


@router.put("/{day}/{meal_type}", response_model=SlotOut)
async def assign_slot(
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

    recipe = await _ensure_recipe_details(db, recipe)

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
        slot.recipe_id = recipe.id
    else:
        slot = MealPlan(
            week_start_date=start,
            day_of_week=day,
            meal_type=meal_type,
            recipe_id=recipe.id,
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
async def autogenerate(week_start: Optional[date] = None, db: Session = Depends(get_db)):
    """Fill empty slots using macro goals. Prefers favorited recipes."""
    start = _monday(week_start or date.today())
    goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
    if not goals:
        goals = MacroGoals(id=1)
        db.add(goals)
        db.commit()
        db.refresh(goals)

    diet, allergens = _load_filters(db)
    recipes = await _seed_recipe_pool(db, diet, allergens)
    if not recipes:
        raise HTTPException(
            status_code=400,
            detail="No recipes available. Search for recipes or check your API key.",
        )

    weekly_targets = {
        "calories": goals.calories * 7,
        "protein": goals.protein * 7,
        "carbs": goals.carbs * 7,
        "fat": goals.fat * 7,
    }
    week_totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    daily_totals: dict[int, dict[str, float]] = {
        i: {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0} for i in range(7)
    }

    existing_slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
    for slot in existing_slots:
        if not slot.recipe:
            continue
        for key in week_totals:
            week_totals[key] += _macro_value(slot.recipe, key)
            daily_totals[slot.day_of_week][key] += _macro_value(slot.recipe, key)

    used_ids: set[int] = {
        s.recipe_id for s in existing_slots if s.recipe_id is not None
    }

    for day in range(7):
        for meal_type in MealType:
            existing = next(
                (
                    s
                    for s in existing_slots
                    if s.day_of_week == day and s.meal_type == meal_type
                ),
                None,
            )
            if existing:
                continue

            meal_target = _meal_targets(goals, meal_type)
            day_remaining = {
                key: max(getattr(goals, key) - daily_totals[day][key], 0)
                for key in MACRO_WEIGHTS
            }
            week_remaining = {
                key: max(weekly_targets[key] - week_totals[key], 0)
                for key in MACRO_WEIGHTS
            }

            scored = sorted(
                recipes,
                key=lambda r: _score_recipe(r, meal_target, day_remaining, week_remaining),
            )
            top = scored[:5]
            # Prefer unused recipes for variety, fall back if pool is small
            unused = [r for r in top if r.id not in used_ids]
            candidates = unused if unused else top
            chosen = random.choice(candidates[:3] if len(candidates) >= 3 else candidates)

            slot = MealPlan(
                week_start_date=start,
                day_of_week=day,
                meal_type=meal_type,
                recipe_id=chosen.id,
            )
            db.add(slot)
            used_ids.add(chosen.id)
            for key in week_totals:
                week_totals[key] += _macro_value(chosen, key)
                daily_totals[day][key] += _macro_value(chosen, key)

    db.commit()

    slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
    daily, weekly = _compute_macros(slots)
    gaps = _compute_macro_gaps(weekly, goals)
    return WeekOut(
        week_start_date=start,
        slots=slots,
        daily_macros=daily,
        weekly_macros=weekly,
        macro_gaps=gaps,
    )
