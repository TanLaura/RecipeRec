# core/engine.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .constraints import ConstraintEngine
from .inventory_adapter import adapt_inventory
from .matcher import match_recipe
from .mode_selector import load_policy, inventory_summary, select_mode
from .scorer import score_recipe
from .diversity import diversify
from .shopping_list import build_shopping_list
from .recipe_source import get_recipes_provider_first, hydrate_fatsecret_details


def recommend(
    inventory_payload: List[Dict[str, Any]],
    restrictions: Optional[List[str]] = None,
    top_k: int = 8,
    debug: bool = False,
    data_path: Path = Path("data/df_parsed.csv"),
    restrictions_path: Path = Path("config/restrictions.json"),
    policy_path: Path = Path("config/policy.json"),
    provider_enabled: bool = True,
) -> Dict[str, Any]:
    """
    Provider-first deterministic recommendation engine with local fallback.

    - Provider (FatSecret) supplies candidates + metadata.
    - Local CSV dataset is fallback if provider fails or returns empty.
    - Deterministic matching/scoring/diversity/shopping list remain the same.
    - Provider detail calls (cook time + instructions) are fetched only for final top results.
    """
    restrictions = restrictions or []

    # ---- Load config ----
    policy = load_policy(policy_path)
    modes_cfg = policy["modes"]

    weights = modes_cfg["ranking"]["weights"]
    expiring_soon_days = modes_cfg["expiring_soon_days"]
    quick_bites_core_lt = modes_cfg["ranking"]["quick_bites_core_count_lt"]
    high_conf_threshold = modes_cfg["ranking"]["high_confidence_coverage_threshold"]

    # ---- Adapt inventory ----
    inv_items = adapt_inventory(inventory_payload, expiring_soon_days=expiring_soon_days)
    inv_set = set([i.canonical_name for i in inv_items])

    inv_sum = inventory_summary(inv_items, expiring_soon_days)
    mode = select_mode(inv_sum["unique_items_count"], policy)

    # ---- Choose provider search terms (simple + deterministic) ----
    # Prefer expiring soon items first to bias candidates.
    inv_terms = list(inv_sum.get("expiring_soon_items", [])) + sorted(list(inv_set))

    # ---- Load recipes (provider-first, local fallback) ----
    # Optional: you can use mode to pass prep_time_to later, but keep simple for now.
    recipes, source_meta = get_recipes_provider_first(
        inv_terms=inv_terms,
        policy=policy,
        local_data_path=data_path,
        provider_enabled=provider_enabled,
        provider_max_results=50,
        provider_prep_time_to=None,
    )

    # ---- Apply hard restrictions ----
    cengine = ConstraintEngine(restrictions_path)
    filtered, exclusion_counts = cengine.filter_recipes(recipes, restrictions)
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

    # ---- Hydrate provider details for top recipes only ----
    # This fills in cook time + instructions when provider is fatsecret.
    top_recipe_dicts = [r for (_, r, *_rest) in top_items]
    if source_meta.source == "fatsecret":
        try:
            hydrate_fatsecret_details(top_recipe_dicts, top_n=len(top_recipe_dicts))
        except Exception as e:
            # Don't fail the whole engine if detail hydration fails.
            source_meta.note += f" | detail_hydration_failed: {type(e).__name__}: {e}"

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
                "recipe_id": r.get("recipe_id"),
                "title": r.get("title") or "",
                "url": r.get("url"),
                "image_url": r.get("image_url"),
                "description": r.get("description"),
                "time_minutes": r.get("time_minutes"),
                "instructions": r.get("instructions"),  # list[str] or None
                "bucket": "quick_bites" if is_quick else "main",
                "score": round(float(s), 3),
                "coverage": round(float(coverage), 3),
                "matched": matched,
                "missing": missing,
                "reasons": reasons,
                "violations": [],
                "source": r.get("provider", source_meta.source),
            }
        )

    resp: Dict[str, Any] = {
        "mode": mode,
        "inventory_summary": inv_sum,
        "recommendations": recommendations,
        "source": source_meta.source,
        "source_note": source_meta.note,
    }

    # ---- Shopping list (only for low_stock / empty_fridge) ----
    if mode in ("low_stock", "empty_fridge"):
        resp["shopping_list"] = build_shopping_list(
            scored_items=scored[:500],
            top_n=8,
            max_missing_considered=3,
            exclude_items=exclude_set,
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
            "provider_candidate_count": getattr(source_meta, "provider_count", 0),
        }

    return resp