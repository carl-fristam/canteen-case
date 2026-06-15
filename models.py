from enum import Enum
from pydantic import BaseModel, Field




# For structured output
class Track(str, Enum):
    meat = "meat"
    vegetarian = "vegetarian"

class Weekday(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"

class DishIngredient(BaseModel):
    """Specifying the ingredient product from the database and how much of the ingredient that the dish uses"""
    product_id: int = Field(description="Real product_id from database")
    product_name: str = Field(description="The exact product_name from database")
    quantity_g: float = Field(description="Positive number grams per portion")

class Dish(BaseModel):
    name: str = Field(description="Name of the dish")
    track: Track
    ingredients: list[DishIngredient] = Field(min_length=2)

class DayPlan(BaseModel):
    day: Weekday
    meat_dish: Dish
    vegetarian_dish: Dish

class WeeklyPlan(BaseModel):
    """5 days with 2 tracks os 10 main courses"""
    days: list[DayPlan] = Field(min_length = 5, max_length = 5)








# Data load model
class Product(BaseModel):
    product_id: int
    product_name: str
    ingredient_group: str
    dietary_class: str
    cost_per_100g_eur: float
    energy_kcal_per_100g: float
    volume_ml_per_100g: float | None # Defaults to None since there are so many missing values (few liquids)
    allergen_gluten: bool
    allergen_nuts: bool
    allergen_dairy: bool
    is_available: bool






# A single named validation check, for transparent reporting in the UI
class Check(BaseModel):
    name: str
    passed: bool
    details: list[str] = []







# Summary models

class TrackSummary(BaseModel):
    total_cost_eur: float = 0.0
    total_calories_kcal: float = 0.0
    allergens: list[str] = []

class WeeklySummary(BaseModel):
    meat_track: TrackSummary
    vegetarian_track: TrackSummary
    grand_total_cost_eur: float = 0.0