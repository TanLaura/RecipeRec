from typing import List, Tuple


def primary_key(item: Tuple) -> str:
    """
    item tuple layout:
      (score, recipe, matched, missing, coverage, core_size, is_quick, uses_expiring)
    """
    _, recipe, matched, _, _, _, _, _ = item
    if matched:
        return matched[0]  # simplest stable heuristic
    # fallback: first ingredient_norm token
    ing = recipe.get("ingredients_norm", [])
    return ing[0] if ing else "unknown"


def diversify(
    scored_items: List[Tuple],
    top_k: int,
    max_per_primary: int = 1,
    dedupe_title: bool = True,
) -> List[Tuple]:
    """
    Greedy re-ranker that keeps high scoring items but enforces diversity.
    """
    results = []
    seen_titles = set()
    counts = {}

    for item in scored_items:
        score, recipe, matched, missing, coverage, core_size, is_quick, uses_expiring = item

        title = (recipe.get("title") or "").strip().lower()
        if dedupe_title and title:
            if title in seen_titles:
                continue

        key = primary_key(item)
        c = counts.get(key, 0)
        if c >= max_per_primary:
            continue

        results.append(item)
        if title:
            seen_titles.add(title)
        counts[key] = c + 1

        if len(results) >= top_k:
            break

    return results