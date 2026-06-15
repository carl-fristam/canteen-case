"""Loads the products table from DuckDB into memory once, then hands this to the LLM:
`candidates()` is the filtered, available set that gets formatted into
the prompt catalogue, while `get()` just keeps the full table around for validation."""

import duckdb

from config import DB_PATH
from models import Product

class ProductStore:
    def __init__(self, db_path: str = DB_PATH):
        self._con = duckdb.connect(db_path, read_only=True)
        self._by_id = {product.product_id: product for product in self._fetch()}
        self._candidates_cache: dict[frozenset[str], list[Product]] = {}

    def get(self, product_id: int) -> Product | None:
        """Look up any product by id from the full table (ignores availability/allergen filters)."""
        return self._by_id.get(product_id)

    def candidates(self, exclude: frozenset[str] = frozenset()) -> list[Product]:
        """Available products the LLM may see, optionally excluding allergens.

        Cached per allergen-filter: the same SELECT isn't re-run on every plan request."""
        if exclude not in self._candidates_cache:
            where_clause = "WHERE is_available = 1"

            for allergen in ("gluten", "nuts", "dairy"):   # fixed names, no injection
                if allergen in exclude:
                    where_clause += f" AND allergen_{allergen} = 0"
            self._candidates_cache[exclude] = self._fetch(where_clause)
        return self._candidates_cache[exclude]

    def _fetch(self, where_clause: str = "") -> list[Product]:
        """Run the products SELECT (plus optional WHERE) and map each row to a Product."""
        
        select_sql = """SELECT product_id, product_name, ingredient_group, dietary_class,
                               cost_per_100g_eur, energy_kcal_per_100g, volume_ml_per_100g,
                               allergen_gluten, allergen_nuts, allergen_dairy, is_available
                        FROM products"""
        
        cursor = self._con.execute(f"{select_sql} {where_clause}") #DuckDB library to execute SQL
        
        columns = [col[0] for col in (cursor.description or [])]
        
        return [Product.model_validate(dict(zip(columns, row))) for row in cursor.fetchall()]