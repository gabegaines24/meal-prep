from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MealPlan
from backend.services import file_gen
from backend.services.grocery import build_grocery_list

router = APIRouter()


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _get_slots(db: Session, start: date) -> list[MealPlan]:
    return db.query(MealPlan).filter(MealPlan.week_start_date == start).all()


class GroceryItem(BaseModel):
    name: str
    recipes: list[str]
    category: str


class GroceryCategory(BaseModel):
    name: str
    items: list[GroceryItem]


class GroceryListOut(BaseModel):
    week_start_date: str
    items: list[GroceryItem]
    categories: list[GroceryCategory]


@router.get("/grocery-list/data", response_model=GroceryListOut)
def get_grocery_list_data(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    if not slots:
        raise HTTPException(status_code=404, detail=f"No meal plan for week starting {start}.")
    return build_grocery_list(start, slots)


@router.get("/grocery-list", response_class=HTMLResponse)
def get_grocery_list(
    week_start: Optional[date] = None,
    db: Session = Depends(get_db),
):
    start = _monday(week_start or date.today())
    slots = _get_slots(db, start)
    if not slots:
        raise HTTPException(status_code=404, detail=f"No meal plan for week starting {start}.")

    html = file_gen.grocery_list_html(week_start=start, slots=slots)
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
