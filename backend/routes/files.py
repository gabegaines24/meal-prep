from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MealPlan, UserProfile
from backend.services import file_gen, pricing as pricing_svc
from backend.services.grocery import build_grocery_list

router = APIRouter()


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _get_slots(db: Session, start: date) -> list[MealPlan]:
    return db.query(MealPlan).filter(MealPlan.week_start_date == start).all()


def _get_profile(db: Session) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.id == 1).first()


class GroceryItem(BaseModel):
    name: str
    recipes: list[str]
    category: str
    price: Optional[float] = None
    price_source: Optional[str] = None
    stale: bool = False


class GroceryCategory(BaseModel):
    name: str
    items: list[GroceryItem]
    subtotal: Optional[float] = None


class BudgetSummary(BaseModel):
    budget: float = 0.0
    estimated_total: float = 0.0
    remaining: float = 0.0
    over_budget: bool = False
    prices_as_of: Optional[str] = None
    stale: bool = False
    store_name: str = ""
    zip_code: str = ""


class GroceryListOut(BaseModel):
    week_start_date: str
    items: list[GroceryItem]
    categories: list[GroceryCategory]
    budget_summary: BudgetSummary


@router.get("/budget-summary")
async def get_budget_summary(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    profile = _get_profile(db)
    return await pricing_svc.price_week(slots, profile, db)


@router.get("/grocery-list/data", response_model=GroceryListOut)
async def get_grocery_list_data(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    if not slots:
        raise HTTPException(status_code=404, detail=f"No meal plan for week starting {start}.")
    profile = _get_profile(db)
    return await build_grocery_list(start, slots, profile, db)


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
    data = await build_grocery_list(start, slots, profile, db)
    html = file_gen.grocery_list_html(week_start=start, grocery_data=data)
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
