from typing import Dict, List, Set, Tuple

PANTRY_IGNORE = {"salt", "pepper", "water"}

def recipe_core(ingredients_norm: List[str]) -> List[str]:
    return [x for x in ingredients_norm if x not in PANTRY_IGNORE]

def match_recipe(recipe: Dict, inventory_set: Set[str]) -> Tuple[List[str], List[str], float, int]:
    core = recipe_core(recipe["ingredients_norm"])
    core_set = set(core)
    if not core_set:
        return [], [], 0.0, 0

    matched = sorted(list(core_set & inventory_set))
    missing = sorted(list(core_set - inventory_set))
    coverage = len(matched) / len(core_set)
    return matched, missing, coverage, len(core_set)