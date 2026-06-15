"""Deterministic checks: does the plan respect the catalogue and track rules?

Returns one named Check per rule so the UI can show exactly what was verified.
"""
from models import Track, WeeklyPlan, Check
from data.product_store import ProductStore


def validate_plan(plan: WeeklyPlan, store: ProductStore,
                  exclude: frozenset[str] = frozenset()) -> list[Check]:
    checks: dict[str, list[str]] = {
        "All products exist in the catalogue": [],
        "All products are available": [],
        "Product names match the catalogue": [],
        "Track labels are consistent": [],
        "Meat tracks contain a meat product": [],
        "Vegetarian tracks are meat-free": [],
        "Quantities are positive": [],
    }
    allergen_key = f"No excluded allergens ({', '.join(sorted(exclude))})" if exclude else None
    if allergen_key:
        checks[allergen_key] = []

    for day in plan.days:
        for dish, slot in ((day.meat_dish, Track.meat),
                           (day.vegetarian_dish, Track.vegetarian)):
            where = f"{day.day.value} / {slot.value} ('{dish.name}')"
            if dish.track != slot:
                checks["Track labels are consistent"].append(
                    f"{where}: dish.track={dish.track.value} but slot is {slot.value}")

            classes_seen: list[str] = []
            for ing in dish.ingredients:
                if ing.quantity_g <= 0:
                    checks["Quantities are positive"].append(
                        f"{where}: '{ing.product_name}' quantity is {ing.quantity_g} g")
                p = store.get(ing.product_id)
                if p is None:
                    checks["All products exist in the catalogue"].append(
                        f"{where}: product_id {ing.product_id} does not exist (hallucinated)")
                    continue
                if not p.is_available:
                    checks["All products are available"].append(
                        f"{where}: '{p.product_name}' (id {ing.product_id}) is not available")
                if p.product_name != ing.product_name:
                    checks["Product names match the catalogue"].append(
                        f"{where}: id {ing.product_id} "
                        f"(plan='{ing.product_name}', catalogue='{p.product_name}')")
                classes_seen.append(p.dietary_class)
                if slot is Track.vegetarian and p.dietary_class == "meat":
                    checks["Vegetarian tracks are meat-free"].append(
                        f"{where}: contains meat product '{p.product_name}'")
                if allergen_key:
                    for a in exclude:
                        if getattr(p, f"allergen_{a}"):
                            checks[allergen_key].append(
                                f"{where}: '{p.product_name}' contains {a}")

            if slot is Track.meat and "meat" not in classes_seen:
                checks["Meat tracks contain a meat product"].append(
                    f"{where}: no meat-class product")

    return [Check(name=name, passed=not fails, details=fails)
            for name, fails in checks.items()]
