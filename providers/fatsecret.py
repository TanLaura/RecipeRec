# providers/fatsecret.py
from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
BASE_REST = "https://platform.fatsecret.com/rest"


@dataclass
class FatSecretConfig:
    client_id: str
    client_secret: str
    scope: str = "basic"


class FatSecretClient:
    """
    Minimal FatSecret client:
    - OAuth2 client_credentials
    - recipes.search.v3
    - recipe.get.v2 (details / directions / cooking_time_min)
    """

    def __init__(self, cfg: FatSecretConfig, timeout_s: int = 30):
        self.cfg = cfg
        self.timeout_s = timeout_s
        self._token: Optional[str] = None

    @staticmethod
    def from_env() -> "FatSecretClient":
        cid = os.getenv("FATSECRET_CLIENT_ID")
        csec = os.getenv("FATSECRET_CLIENT_SECRET")
        if not cid or not csec:
            raise RuntimeError("Missing FATSECRET_CLIENT_ID / FATSECRET_CLIENT_SECRET environment variables")
        return FatSecretClient(FatSecretConfig(client_id=cid, client_secret=csec))

    def get_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "scope": self.cfg.scope},
            auth=(self.cfg.client_id, self.cfg.client_secret),
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"FatSecret token error: {data['error']}")
        self._token = data["access_token"]
        return self._token

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{BASE_REST}{path}"
        resp = requests.get(url, headers=headers, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        # FatSecret can return HTTP 200 with embedded error object
        if "error" in data:
            raise RuntimeError(f"FatSecret API error: {data['error']}")
        return data

    def recipes_search_v3(
        self,
        search_expression: str,
        max_results: int = 50,
        page_number: int = 0,
        must_have_images: bool = True,
        prep_time_to: Optional[int] = None,
        recipe_types: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "format": "json",
            "search_expression": search_expression,
            "max_results": max_results,
            "page_number": page_number,
            "must_have_images": "true" if must_have_images else "false",
        }
        if prep_time_to is not None:
            params["prep_time.to"] = str(prep_time_to)
        if recipe_types:
            params["recipe_types"] = recipe_types

        data = self._get("/recipes/search/v3", params)
        recipes = data.get("recipes", {}).get("recipe", [])
        if isinstance(recipes, dict):
            recipes = [recipes]
        return recipes

    def recipe_get_v2(self, recipe_id: str | int) -> Dict[str, Any]:
        params = {"format": "json", "recipe_id": str(recipe_id)}
        data = self._get("/recipe/v2", params)
        # returns {"recipe": {...}}
        return data.get("recipe", data)


def normalize_search_expression(terms: List[str], max_terms: int = 6) -> str:
    # very simple: join top terms; FatSecret searches on expression string
    terms = [t.strip() for t in terms if t and t.strip()]
    return " ".join(terms[:max_terms])