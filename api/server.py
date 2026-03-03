from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.engine import recommend

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "df_parsed.csv"
DEFAULT_RESTRICTIONS_PATH = ROOT_DIR / "config" / "restrictions.json"
DEFAULT_POLICY_PATH = ROOT_DIR / "config" / "policy.json"


class InventoryItem(BaseModel):
    name: str
    expiration_date: Optional[str] = None
    category: Optional[str] = None
    purchase_date: Optional[str] = None
    quantity: Optional[float] = None


class RecommendRequest(BaseModel):
    inventory: List[InventoryItem] = Field(default_factory=list)
    restrictions: Optional[List[str]] = None
    top_k: int = 8
    debug: bool = False
    provider_enabled: bool = True


class RecommendResponse(BaseModel):
    mode: str
    inventory_summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    source: str
    source_note: str
    shopping_list: Optional[List[Dict[str, Any]]] = None
    debug: Optional[Dict[str, Any]] = None


app = FastAPI(title="Recipe Recommender v2", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/recommend", response_model=RecommendResponse)
def recommend_endpoint(payload: RecommendRequest) -> Dict[str, Any]:
    result = recommend(
        inventory_payload=[item.model_dump() for item in payload.inventory],
        restrictions=payload.restrictions,
        top_k=payload.top_k,
        debug=payload.debug,
        data_path=DEFAULT_DATA_PATH,
        restrictions_path=DEFAULT_RESTRICTIONS_PATH,
        policy_path=DEFAULT_POLICY_PATH,
        provider_enabled=payload.provider_enabled,
    )
    return result
