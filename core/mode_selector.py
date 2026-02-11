import json
from pathlib import Path

def load_policy(policy_path: Path) -> dict:
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy config not found: {policy_path}")

    raw = policy_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"Policy config is empty: {policy_path}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Policy config is not valid JSON: {policy_path}\n{e}") from e


def inventory_summary(inv_items, expiring_soon_days: int) -> dict:
    canonical = [i.canonical_name for i in inv_items]
    unique = sorted(list(set(canonical)))

    expiring = [i.canonical_name for i in inv_items if i.is_expiring_soon]
    expiring_unique = sorted(list(set(expiring)))

    return {
        "unique_items_count": len(unique),
        "expiring_soon_count": len(expiring_unique),
        "expiring_soon_items": expiring_unique,
    }


def select_mode(unique_items_count: int, policy: dict) -> str:
    ms = policy["modes"]["mode_selection"]

    if unique_items_count < ms["empty_fridge"]["unique_items_count_lt"]:
        return "empty_fridge"
    if unique_items_count < ms["low_stock"]["unique_items_count_lt"]:
        return "low_stock"
    return "abundant"