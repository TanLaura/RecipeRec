# core/shopping_list.py
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple

# Non-actionable / vague tokens you don't want in shopping suggestions
BLOCKLIST: Set[str] = {"vegetable", "vegetables"}


def build_shopping_list(
    scored_items: List[Tuple],
    top_n: int = 8,
    max_missing_considered: int = 3,
    exclude_items: Optional[Set[str]] = None,
) -> List[Dict]:
    """
    Build a shopping list from the scored candidate list.

    scored_items tuple layout:
      (score, recipe, matched, missing, coverage, core_size, is_quick, uses_expiring)

    Strategy:
    - Only consider candidates that are "close" (missing <= max_missing_considered)
    - Count missing ingredients across those candidates
    - Filter out vague tokens (BLOCKLIST)
    - Filter out restricted ingredients (exclude_items)
    - Return top_n ingredients with unlock_value counts
    """
    exclude_items = set([x.strip().lower() for x in (exclude_items or set()) if isinstance(x, str)])

    counter = Counter()

    for (score, recipe, matched, missing, coverage, core_size, is_quick, uses_expiring) in scored_items:
        if len(missing) == 0:
            continue
        if len(missing) > max_missing_considered:
            continue

        # Normalize + filter
        filtered_missing = []
        for m in missing:
            m_norm = str(m).strip().lower()
            if not m_norm:
                continue
            if m_norm in BLOCKLIST:
                continue
            if m_norm in exclude_items:
                continue
            filtered_missing.append(m_norm)

        if filtered_missing:
            counter.update(filtered_missing)

    items: List[Dict] = []
    for ing, cnt in counter.most_common(top_n):
        items.append(
            {
                "item": ing,
                "count": cnt,         # appears in cnt near-miss recipes
                "unlock_value": cnt,  # same metric for now
            }
        )

    return items