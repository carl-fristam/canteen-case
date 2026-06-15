from schemas import WeeklyPlan, DayPlan, Dish, DishIngredient, Track, Weekday, Product
from data.product_store import ProductStore
from services.validate import validate_plan

def test_validator_detects_hallucination():
    store = ProductStore()
    # Create a plan with a fake product_id
    ing = DishIngredient(product_id=99999, product_name="Magic Beans", quantity_g=100)
    dish = Dish(name="Hallucinated Dish", track=Track.meat, ingredients=[ing, ing])
    
    # Simple 1-day plan for testing (normally 5)
    plan = WeeklyPlan(days=[
        DayPlan(day=Weekday.monday, meat_dish=dish, vegetarian_dish=dish),
        DayPlan(day=Weekday.tuesday, meat_dish=dish, vegetarian_dish=dish),
        DayPlan(day=Weekday.wednesday, meat_dish=dish, vegetarian_dish=dish),
        DayPlan(day=Weekday.thursday, meat_dish=dish, vegetarian_dish=dish),
        DayPlan(day=Weekday.friday, meat_dish=dish, vegetarian_dish=dish),
    ])
    
    checks = validate_plan(plan, store)
    hallucination_check = next(c for c in checks if c.name == "All products exist in the catalogue")
    assert hallucination_check.passed is False
    assert "99999 does not exist" in hallucination_check.details[0]

def test_validator_detects_meat_in_vegetarian_track():
    store = ProductStore()
    # Get a meat product
    meat_p = next(p for p in store.candidates() if p.dietary_class == "meat")
    ing = DishIngredient(product_id=meat_p.product_id, product_name=meat_p.product_name, quantity_g=100)
    
    # Put meat in a vegetarian dish
    veg_dish = Dish(name="Fake Veggie", track=Track.vegetarian, ingredients=[ing, ing])
    meat_dish = Dish(name="Real Meat", track=Track.meat, ingredients=[ing, ing])
    
    plan = WeeklyPlan(days=[
        DayPlan(day=d, meat_dish=meat_dish, vegetarian_dish=veg_dish)
        for d in Weekday
    ])
    
    checks = validate_plan(plan, store)
    veg_check = next(c for c in checks if c.name == "Vegetarian tracks are meat-free")
    assert veg_check.passed is False
    assert "contains meat product" in veg_check.details[0]
