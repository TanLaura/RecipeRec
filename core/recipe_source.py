# core/recipe_source.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .dataset_adapter import load_recipes
from .canonicalizer import parse_ingredients  # assumes you already have this
from providers.fatsecret import FatSecretClient, normalize_search_expression


@dataclass
class SourceMeta:
    source: str  # "fatsecret" or "local_fallback"
    note: str = ""
    provider_count: int = 0


def _fatsecret_to_internal(recipe_obj: Dict[str, Any]) -> Dict[str, Any]:
    rid = str(recipe_obj.get("recipe_id", ""))
    title = recipe_obj.get("recipe_name", "") or ""
    desc = recipe_obj.get("recipe_description")
    image_url = recipe_obj.get("recipe_image")

    # ---- FIXED INGREDIENT EXTRACTION ----
    ingredients_raw_list = []

    raw_ing = recipe_obj.get("recipe_ingredients")

    if isinstance(raw_ing, dict):
        # structure: {"ingredient": [...]}
        ing_list = raw_ing.get("ingredient", [])
        if isinstance(ing_list, list):
            ingredients_raw_list = [str(x) for x in ing_list]
        elif isinstance(ing_list, str):
            ingredients_raw_list = [ing_list]

    elif isinstance(raw_ing, list):
        ingredients_raw_list = [str(x) for x in raw_ing]

    elif isinstance(raw_ing, str):
        # comma separated string fallback
        ingredients_raw_list = [x.strip() for x in raw_ing.split(",") if x.strip()]

    # Normalize using canonicalizer
    ing_text = " ".join(ingredients_raw_list)
    ingredients_norm = parse_ingredients(ing_text)

    return {
        "recipe_id": f"fatsecret:{rid}",
        "provider_recipe_id": rid,
        "title": title,
        "url": None,
        "image_url": image_url,
        "description": desc,
        "ingredients_raw": ingredients_raw_list,
        "ingredients_norm": ingredients_norm,
        "nutrition": recipe_obj.get("recipe_nutrition"),
        "time_minutes": None,
        "instructions": None,
        "provider": "fatsecret",
    }


def get_recipes_provider_first(
    inv_terms: List[str],
    policy: Dict[str, Any],
    local_data_path: Path,
    provider_enabled: bool = True,
    provider_max_results: int = 50,
    provider_prep_time_to: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], SourceMeta]:
    """
    Try FatSecret first. If fails or returns 0, load local CSV dataset.
    """
    if provider_enabled:
        try:
            client = FatSecretClient.from_env()
            expr = normalize_search_expression(inv_terms, max_terms=6)
            if not expr:
                raise RuntimeError("Empty search_expression")

            # Pull a candidate pool
            provider_max_results = max(1, min(50, int(provider_max_results)))
            raw = client.recipes_search_v3(
                search_expression=expr,
                max_results=provider_max_results,
                must_have_images=True,
                prep_time_to=provider_prep_time_to,
            )
            print("DEBUG provider raw_count:", len(raw))
            internal = [_fatsecret_to_internal(x) for x in raw]
            print("DEBUG provider internal_count:", len(internal))
            if internal:
                print("DEBUG provider ingredients_norm sample:", internal[0].get("ingredients_norm"))
            internal = [r for r in internal if r.get("ingredients_norm")]  # drop empty
            if internal:
                return internal, SourceMeta(source="fatsecret", note=f"expr='{expr}'", provider_count=len(internal))
        except Exception as e:
            # fall through to local
            note = f"Provider failed: {type(e).__name__}: {e}"
            local = load_recipes(local_data_path)
            return local, SourceMeta(source="local_fallback", note=note, provider_count=0)

    # provider disabled
    local = load_recipes(local_data_path)
    return local, SourceMeta(source="local_fallback", note="Provider disabled", provider_count=0)


def hydrate_fatsecret_details(recipes: List[Dict[str, Any]], top_n: int = 8) -> None:
    """
    For top recipes only, fetch details (cook time + directions) via recipe.get.v2.
    Mutates recipe dicts in-place.
    """
    client = FatSecretClient.from_env()
    for r in recipes[:top_n]:
        if r.get("provider") != "fatsecret":
            continue
        rid = r.get("provider_recipe_id")
        if not rid:
            continue

        detail = client.recipe_get_v2(rid)

        # cook time
        ct = detail.get("cooking_time_min")
        try:
            r["time_minutes"] = int(ct) if ct is not None else None
        except Exception:
            r["time_minutes"] = None

        # directions: {"directions":{"direction":[{"direction_description":...}, ...]}}
        directions = detail.get("directions", {}).get("direction", [])
        if isinstance(directions, dict):
            directions = [directions]
        steps = []
        for d in directions:
            desc = d.get("direction_description")
            if desc:
                steps.append(desc.strip())
        r["instructions"] = steps if steps else None