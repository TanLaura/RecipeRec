# core/constraints.py
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ConstraintEngine:
    def __init__(self, restrictions_config_path: Path):
        if not restrictions_config_path.exists():
            raise FileNotFoundError(f"Restrictions config not found: {restrictions_config_path}")

        raw = restrictions_config_path.read_text(encoding="utf-8").strip()
        if not raw:
            raise ValueError(f"Restrictions config is empty: {restrictions_config_path}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Restrictions config is not valid JSON: {restrictions_config_path}\n{e}"
            ) from e

        self.restrictions = data.get("restrictions", [])

    def build_exclude_set(self, active_restrictions: List[str]) -> Set[str]:
        """
        Build a set of excluded ingredient phrases for all active restrictions.
        Used to prevent restricted items appearing in shopping list suggestions.
        """
        exclude: Set[str] = set()
        active = set(active_restrictions or [])

        for rule in self.restrictions:
            rid = rule.get("id")
            if rid not in active:
                continue
            for phrase in rule.get("exclude_phrases", []):
                if isinstance(phrase, str) and phrase.strip():
                    exclude.add(phrase.strip().lower())

        return exclude

    def recipe_violates(self, recipe: Dict, active_restrictions: List[str]) -> List[str]:
        """
        Returns a list of violated restriction IDs.
        Current strategy: exact phrase match against recipe['ingredients_norm'].
        """
        violations: List[str] = []
        active = set(active_restrictions or [])

        # Make sure ingredients_norm exists and is lowercase-ish
        ing_norm = set([str(x).strip().lower() for x in recipe.get("ingredients_norm", [])])

        for rule in self.restrictions:
            rid = rule.get("id")
            if rid not in active:
                continue

            exclude_phrases = rule.get("exclude_phrases", [])
            for phrase in exclude_phrases:
                p = str(phrase).strip().lower()
                if not p:
                    continue
                if p in ing_norm:
                    violations.append(rid)
                    break

        return violations

    def filter_recipes(
        self, recipes: List[Dict], active_restrictions: List[str]
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Returns:
          filtered_recipes,
          exclusion_counts (how many recipes were excluded by each rule)
        """
        exclusion_counts = {r.get("id"): 0 for r in self.restrictions if r.get("id")}
        filtered: List[Dict] = []

        for recipe in recipes:
            violations = self.recipe_violates(recipe, active_restrictions)
            if violations:
                for v in violations:
                    if v in exclusion_counts:
                        exclusion_counts[v] += 1
                continue
            filtered.append(recipe)

        return filtered, exclusion_counts