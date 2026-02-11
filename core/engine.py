# core/engine.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .constraints import ConstraintEngine
from .dataset_adapter import load_recipes
from .inventory_adapter import adapt_inventory
from .matcher import match_recipe
from .mode_selector import load_policy, inventory_summary, select_mode
from .scorer import score_recipe
from .diversity import diversify
from .shopping_list import build_shopping_list


def recommend(
    inventory_payload: List[Dict[str, Any]],
    restrictions: Optional[List[str]] = None,
    top_k: int = 8,
    debug: bool = False,
    data_path: Path = Path("data/df_parsed.csv"),
    restrictions_path: Path = Path("config/restrictions.json"),
    policy_path: Path = Path("config/policy.json"),
) -> Dict[str, Any]:
    """
    End-to-end deterministic recommendation engine.

    Inputs
    - inventory_payload: list of inventory dicts (from app)
    - restrictions: list of restriction ids (e.g., ["allergy_nuts", "diet_vegan"])
    - top_k: number of recipes to return
    - debug: include debug info in response

    Output
    - dict with: mode, inventory_summary, recommendations, (optional) shopping_list, debug
    """
    restrictions = restrictions or []

    # ---- Load config ----
    policy = load_policy(policy_path)
    modes_cfg = policy["modes"]

    weights = modes_cfg["ranking"]["weights"]
    expiring_soon_days = modes_cfg["expiring_soon_days"]
    quick_bites_core_lt = modes_cfg["ranking"]["quick_bites_core_count_lt"]
    high_conf_threshold = modes_cfg["ranking"]["high_confidence_coverage_threshold"]

    # ---- Load recipes ----
    recipes = load_recipes(data_path)

    # ---- Adapt inventory ----
    inv_items = adapt_inventory(inventory_payload, expiring_soon_days=expiring_soon_days)
    inv_set = set([i.canonical_name for i in inv_items])

    inv_sum = inventory_summary(inv_items, expiring_soon_days)
    mode = select_mode(inv_sum["unique_items_count"], policy)

    # ---- Apply hard restrictions ----
    cengine = ConstraintEngine(restrictions_path)
    filtered, exclusion_counts = cengine.filter_recipes(recipes, restrictions)

    # Build exclude set for shopping list safety
    exclude_set = cengine.build_exclude_set(restrictions)

    # ---- Candidate thresholds by mode ----
    cg = modes_cfg["candidate_generation"][mode]
    min_matched = cg["min_matched_core"]
    max_missing = cg["max_missing_core"]

    expiring_set = set(inv_sum["expiring_soon_items"])

    # ---- Score all candidates ----
    scored = []
    for r in filtered:
        matched, missing, coverage, core_size = match_recipe(r, inv_set)

        if len(matched) < min_matched:
            continue
        if len(missing) > max_missing:
            continue

        is_quick = core_size < quick_bites_core_lt
        uses_expiring = any(x in expiring_set for x in matched)

        s = score_recipe(
            coverage=coverage,
            matched_count=len(matched),
            missing_count=len(missing),
            core_size=core_size,
            is_quick_bites=is_quick,
            uses_expiring_soon=uses_expiring,
            weights=weights,
        )

        scored.append((s, r, matched, missing, coverage, core_size, is_quick, uses_expiring))

    scored.sort(reverse=True, key=lambda x: x[0])

    # ---- Cap quick_bites via policy ----
    presentation_cfg = modes_cfg.get("presentation", {})
    max_quick_by_mode = presentation_cfg.get("max_quick_by_mode", {})
    max_quick = int(max_quick_by_mode.get(mode, top_k))

    capped = []
    quick_count = 0
    for item in scored:
        is_quick = item[6]
        if is_quick and quick_count >= max_quick:
            continue
        if is_quick:
            quick_count += 1
        capped.append(item)

    # ---- Diversity via policy ----
    div_cfg = modes_cfg.get("diversity", {})
    top_items = diversify(
        capped,
        top_k=top_k,
        max_per_primary=int(div_cfg.get("max_per_primary_ingredient", 1)),
        dedupe_title=bool(div_cfg.get("dedupe_same_title", True)),
    )

    # ---- Build response recommendations ----
    recommendations: List[Dict[str, Any]] = []
    for s, r, matched, missing, coverage, core_size, is_quick, uses_expiring in top_items:
        reasons = []
        if coverage >= high_conf_threshold:
            reasons.append("High match")
        if uses_expiring:
            reasons.append("Uses expiring soon items")
        if restrictions:
            reasons.append("Passes dietary restrictions")

        recommendations.append(
            {
                "recipe_id": r["recipe_id"],
                "title": r.get("title") or "",
                "url": r.get("url"),
                "bucket": "quick_bites" if is_quick else "main",
                "score": round(float(s), 3),
                "coverage": round(float(coverage), 3),
                "matched": matched,
                "missing": missing,
                "reasons": reasons,
                "violations": [],
            }
        )

    resp: Dict[str, Any] = {
        "mode": mode,
        "inventory_summary": inv_sum,
        "recommendations": recommendations,
    }

    # ---- Shopping list (only for low_stock / empty_fridge) ----
    if mode in ("low_stock", "empty_fridge"):
        resp["shopping_list"] = build_shopping_list(
            scored_items=scored[:500],  # keep it fast + relevant
            top_n=8,
            max_missing_considered=3,
            exclude_items=exclude_set,  # prevent restricted ingredients
        )

    # ---- Debug info ----
    if debug:
        titles = [(x.get("title") or "").strip().lower() for x in recommendations if x.get("title")]
        resp["debug"] = {
            "exclusion_counts": exclusion_counts,
            "candidate_thresholds": cg,
            "inventory_set": sorted(list(inv_set)),
            "scored_count": len(scored),
            "quick_bites_cap": max_quick,
            "duplicate_titles_in_top": len(titles) - len(set(titles)),
            "shopping_exclude_set_size": len(exclude_set),
        }

    return resp