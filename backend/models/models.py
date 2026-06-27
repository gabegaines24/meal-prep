import enum

from sqlalchemy import Boolean, Column, Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    spoonacular_id = Column(Integer, unique=True, index=True, nullable=True)
    title = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    ingredients_json = Column(String, nullable=True)   # JSON list of ingredient strings
    instructions_json = Column(String, nullable=True)  # JSON list of step strings
    estimated_cost = Column(Float, nullable=True)      # dollars, from Kroger pricing
    favorited = Column(Boolean, default=False)

    meal_slots = relationship("MealPlan", back_populates="recipe")


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday … 6 = Sunday
    meal_type = Column(Enum(MealType), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)

    recipe = relationship("Recipe", back_populates="meal_slots")


class MacroGoals(Base):
    __tablename__ = "macro_goals"

    id = Column(Integer, primary_key=True, default=1)
    calories = Column(Float, default=2000.0)
    protein = Column(Float, default=150.0)
    carbs = Column(Float, default=200.0)
    fat = Column(Float, default=65.0)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, default=1)
    store_name = Column(String, default="")
    kroger_location_id = Column(String, default="")
    weekly_budget = Column(Float, default=0.0)
    allergens_json = Column(String, default="[]")  # JSON list, e.g. ["peanuts", "gluten"]
    diet_type = Column(String, default="")         # Spoonacular value or empty
