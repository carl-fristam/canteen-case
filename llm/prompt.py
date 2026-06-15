"""Catalogue formatting + the shared system prompt for the planner."""
from schemas import Product

SYSTEM = (
    """
    You plan a university canteen's weekly lunch menu: Monday-Friday, two tracks per day.
    Each dish is a balanced main (carb base + protein + vegetables + a sauce/dressing).
    Rules:
    - Use only products from the catalogue below. Copy product_id and product_name verbatim; never invent any products.
    - Meat track: include at least one dietary_class='meat' product (this covers fish/seafood). Sides may be vegetarian/vegan).
    - Vegetarian track: only dietary_class 'vegan' or 'vegetarian'. No meat.
    - Quantities are grams per portion and must be positive.
    """
)


def format_catalogue(products: list[Product]) -> str:
    lines = ["product_id|name|group|dietary_class|kcal/100g|eur/100g|allergens"]
    for p in products:
        allergens = ",".join(
            a for a, on in (("gluten", p.allergen_gluten),
                            ("nuts", p.allergen_nuts),
                            ("dairy", p.allergen_dairy)) if on
        ) or "none"
        lines.append(
            f"{p.product_id}|{p.product_name}|{p.ingredient_group}|"
            f"{p.dietary_class}|{p.energy_kcal_per_100g:.0f}|"
            f"{p.cost_per_100g_eur:.2f}|{allergens}"
        )
    return "\n".join(lines)
