"""Deterministic checks: does the plan respect the catalogue and track rules?

Any failure makes the plan invalid. Returns a flat list of error strings.
"""
from schemas import Track, WeeklyPlan
from data.product_store import ProductStore


def validate_plan(plan: WeeklyPlan, store: ProductStore,
                  exclude: frozenset[str] = frozenset()) -> list[str]:
    errors = []

    for day in plan.days:
        for dish, slot in ((day.meat_dish, Track.meat),
                           (day.vegetarian_dish, Track.vegetarian)):
            where = f"{day.day.value} / {slot.value} ('{dish.name}')"
            if dish.track != slot:
                errors.append(f"{where}: track mismatch (dish says {dish.track.value})")

            has_meat = False
            for ing in dish.ingredients:
                if ing.quantity_g <= 0:
                    errors.append(f"{where}: '{ing.product_name}' quantity is {ing.quantity_g}g")
                
                p = store.get(ing.product_id)
                if p is None:
                    errors.append(f"{where}: product_id {ing.product_id} does not exist")
                    continue
                
                if not p.is_available:
                    errors.append(f"{where}: '{p.product_name}' is not available")
                
                # Sync name from store
                ing.product_name = p.product_name
                if p.dietary_class == "meat":
                    has_meat = True
                    if slot is Track.vegetarian:
                        errors.append(f"{where}: contains meat product '{p.product_name}'")
                
                for a in exclude:
                    if getattr(p, f"allergen_{a}"):
                        errors.append(f"{where}: '{p.product_name}' contains {a}")

            if slot is Track.meat and not has_meat:
                errors.append(f"{where}: no meat-class product in meat track")

    return errors
