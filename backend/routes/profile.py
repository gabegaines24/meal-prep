import json
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import UserProfile

router = APIRouter()

VALID_DIETS = {
    "gluten free", "ketogenic", "vegetarian", "lacto-vegetarian",
    "ovo-vegetarian", "vegan", "pescetarian", "paleo", "primal", "whole30", "",
}

VALID_ALLERGENS = {
    "dairy", "egg", "gluten", "grain", "peanut", "seafood",
    "sesame", "shellfish", "soy", "sulfite", "tree nut", "wheat",
}


class ProfileSchema(BaseModel):
    store_name: str = ""
    kroger_location_id: str = ""
    weekly_budget: float = 0.0
    allergens: list[str] = []
    diet_type: str = ""

    model_config = {"from_attributes": True}


def _get_or_create(db: Session) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
    if not profile:
        profile = UserProfile(id=1)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _to_schema(profile: UserProfile) -> ProfileSchema:
    allergens: list[str] = []
    try:
        allergens = json.loads(profile.allergens_json or "[]")
    except json.JSONDecodeError:
        pass
    return ProfileSchema(
        store_name=profile.store_name or "",
        kroger_location_id=profile.kroger_location_id or "",
        weekly_budget=profile.weekly_budget or 0.0,
        allergens=allergens,
        diet_type=profile.diet_type or "",
    )


@router.get("", response_model=ProfileSchema)
def get_profile(db: Session = Depends(get_db)):
    return _to_schema(_get_or_create(db))


@router.put("", response_model=ProfileSchema)
def update_profile(payload: ProfileSchema, db: Session = Depends(get_db)):
    profile = _get_or_create(db)
    profile.store_name = payload.store_name
    profile.kroger_location_id = payload.kroger_location_id
    profile.weekly_budget = payload.weekly_budget
    profile.allergens_json = json.dumps(payload.allergens)
    profile.diet_type = payload.diet_type
    db.commit()
    db.refresh(profile)
    return _to_schema(profile)
