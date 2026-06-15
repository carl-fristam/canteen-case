"""A no-cost stand-in for plan_week — builds a valid plan from real products."""
from schemas import WeeklyPlan, DayPlan, Dish, DishIngredient, Track, Product, Weekday


def fake_plan_week(products: list[Product]) -> WeeklyPlan:
    meat = next(p for p in products if p.dietary_class == "meat")
    veg = [p for p in products if p.dietary_class in ("vegan", "vegetarian")][:2]

    def ing(p: Product, q: float = 150.0) -> DishIngredient:
        return DishIngredient(product_id=p.product_id, product_name=p.product_name, quantity_g=q)

    meat_dish = Dish(name="Test meat main", track=Track.meat,
                     ingredients=[ing(meat), ing(veg[0]), ing(veg[1])])
    veg_dish = Dish(name="Test veg main", track=Track.vegetarian,
                    ingredients=[ing(veg[0]), ing(veg[1])])

    return WeeklyPlan(days=[
        DayPlan(day=d, meat_dish=meat_dish, vegetarian_dish=veg_dish)
        for d in Weekday
    ])
