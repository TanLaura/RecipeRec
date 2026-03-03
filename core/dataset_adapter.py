from functools import lru_cache
from pathlib import Path

import pandas as pd

from .canonicalizer import parse_ingredients

@lru_cache(maxsize=4)
def load_recipes(csv_path: Path):
    df = pd.read_csv(csv_path)

    recipes = []

    for idx, row in df.iterrows():
        title = row.get("recipe_name")
        url = row.get("recipe_urls")
        ingredients_raw = row.get("ingredients_parsed")

        if not isinstance(ingredients_raw, str):
            continue

        ingredients_norm = parse_ingredients(ingredients_raw)

        recipe = {
            "recipe_id": f"jamie_{idx}",
            "title": title,
            "url": url,
            "ingredients_raw": ingredients_raw,
            "ingredients_norm": ingredients_norm
        }

        recipes.append(recipe)

    return recipes