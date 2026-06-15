from schemas import WeeklyPlan, WeeklySummary, TrackSummary, Track
from data.product_store import ProductStore

def summarize_plan(plan: WeeklyPlan, store: ProductStore) -> WeeklySummary:
    meat_sum = TrackSummary()
    veg_sum = TrackSummary()
    
    meat_allergens = set()
    veg_allergens = set()

    for day in plan.days:
        for dish, summary, allergen_set in [
            (day.meat_dish, meat_sum, meat_allergens),
            (day.vegetarian_dish, veg_sum, veg_allergens)
        ]:
            for ing in dish.ingredients:
                p = store.get(ing.product_id)
                if not p:
                    continue
                
                # Calculations are per 100g
                factor = ing.quantity_g / 100.0
                summary.total_cost_eur += p.cost_per_100g_eur * factor
                summary.total_calories_kcal += p.energy_kcal_per_100g * factor
                
                if p.allergen_gluten: allergen_set.add("gluten")
                if p.allergen_nuts: allergen_set.add("nuts")
                if p.allergen_dairy: allergen_set.add("dairy")

    meat_sum.allergens = sorted(list(meat_allergens))
    veg_sum.allergens = sorted(list(veg_allergens))
    
    return WeeklySummary(
        meat_track=meat_sum,
        vegetarian_track=veg_sum,
        grand_total_cost_eur=meat_sum.total_cost_eur + veg_sum.total_cost_eur
    )
