import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import UserProfile

router = APIRouter()


class ProfileSchema(BaseModel):
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
        allergens=allergens,
        diet_type=profile.diet_type or "",
    )


@router.get("", response_model=ProfileSchema)
def get_profile(db: Session = Depends(get_db)):
    return _to_schema(_get_or_create(db))


@router.put("", response_model=ProfileSchema)
def update_profile(payload: ProfileSchema, db: Session = Depends(get_db)):
    profile = _get_or_create(db)
    profile.allergens_json = json.dumps(payload.allergens)
    profile.diet_type = payload.diet_type
    db.commit()
    db.refresh(profile)
    return _to_schema(profile)
