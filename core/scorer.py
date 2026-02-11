import math
from typing import Dict, List, Set, Tuple


def score_recipe(
    coverage: float,
    matched_count: int,
    missing_count: int,
    core_size: int,
    is_quick_bites: bool,
    uses_expiring_soon: bool,
    weights: Dict,
) -> float:
    """
    Deterministic score. Goals:
    - reward coverage
    - lightly reward larger core (avoid single-ingredient dominating)
    - penalize missing
    - penalize quick bites a bit in abundant mode
    - boost using expiring soon items
    """
    s = 0.0
    s += weights["coverage"] * coverage

    # Core size bonus (log): core=1 => 0, core=3 => ~1.1, core=8 => ~2.1
    if core_size > 1:
        s += weights["core_size_bonus_log"] * math.log(core_size)
    else:
        s -= 0.15  # discourage trivial 1-ingredient recipes

    s += weights["missing_penalty"] * missing_count

    if is_quick_bites:
        s += weights["quick_bites_penalty"]

    if uses_expiring_soon:
        s += weights["expiring_soon_boost"]

    return s