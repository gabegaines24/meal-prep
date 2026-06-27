from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import MacroGoals

router = APIRouter()


class GoalsSchema(BaseModel):
    calories: float
    protein: float
    carbs: float
    fat: float

    model_config = {"from_attributes": True}


def _get_or_create(db: Session) -> MacroGoals:
    goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
    if not goals:
        goals = MacroGoals(id=1)
        db.add(goals)
        db.commit()
        db.refresh(goals)
    return goals


@router.get("", response_model=GoalsSchema)
def get_goals(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=GoalsSchema)
def update_goals(payload: GoalsSchema, db: Session = Depends(get_db)):
    goals = _get_or_create(db)
    goals.calories = payload.calories
    goals.protein = payload.protein
    goals.carbs = payload.carbs
    goals.fat = payload.fat
    db.commit()
    db.refresh(goals)
    return goals
