"""In-memory store over the products table (read-only DuckDB access)."""

import duckdb

from config import DB_PATH
from models import Product

class ProductStore:
    def __init__(self, db_path: str = DB_PATH):
        self._con = duckdb.connect(db_path, read_only=True)
        self._by_id = {p.product_id: p for p in self._fetch()}

    def get(self, product_id: int) -> Product | None:
        return self._by_id.get(product_id)

    def candidates(self, exclude: frozenset[str] = frozenset()) -> list[Product]:
        """Available products the LLM may see, optionally excluding allergens."""
        where = "WHERE is_available = 1"
        for allergen in ("gluten", "nuts", "dairy"):   # fixed names → no injection
            if allergen in exclude:
                where += f" AND allergen_{allergen} = 0"
        return self._fetch(where)

    def _fetch(self, where: str = "") -> list[Product]:
        sql = """SELECT product_id, product_name, ingredient_group, dietary_class,
                        cost_per_100g_eur, energy_kcal_per_100g, volume_ml_per_100g,
                        allergen_gluten, allergen_nuts, allergen_dairy, is_available
                 FROM products"""
        cur = self._con.execute(f"{sql} {where}")
        cols = [c[0] for c in (cur.description or [])]
        return [Product.model_validate(dict(zip(cols, r))) for r in cur.fetchall()]
