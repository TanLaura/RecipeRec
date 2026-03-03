# Recommender v2 -- Deterministic Recipe Engine

## Overview

This module provides a deterministic, policy-driven recipe
recommendation engine.

It takes: - User inventory - Dietary restrictions

And returns: - Mode-aware recommendations - Matched/missing breakdown -
Shopping list (for low stock / empty fridge) - Optional debug
diagnostics

The engine is fully config-driven and safe to integrate into backend
services.

------------------------------------------------------------------------

# Architecture Overview

Inventory (app) ↓ Inventory Adapter ↓ Canonicalizer ↓ Mode Selector
(policy-driven) ↓ Restriction Engine ↓ Candidate Generator ↓ Scorer ↓
Quick-Bites Cap ↓ Diversity Reranker ↓ Shopping List Builder ↓ Final
Response

------------------------------------------------------------------------

# Folder Structure

Recommender v2/

core/ - engine.py ← main entry point\
- dataset_adapter.py ← loads df_parsed.csv\
- canonicalizer.py ← phrase + alias normalization\
- inventory_adapter.py ← converts inventory payload\
- constraints.py ← dietary restriction filtering\
- matcher.py ← matched / missing / coverage\
- scorer.py ← score calculation\
- diversity.py ← reranking for variety\
- shopping_list.py ← near-miss aggregation\
- mode_selector.py ← policy loading + mode logic

config/ - policy.json ← scoring & thresholds (editable)\
- restrictions.json ← hard restriction rules\
- actions.json ← reserved (future use)

data/ - df_parsed.csv ← normalized recipe dataset

run_local.py ← local test harness

------------------------------------------------------------------------

# Entry Point

core/engine.py

Function:

recommend( inventory_payload: List\[Dict\], restrictions: List\[str\] =
None, top_k: int = 8, debug: bool = False ) -\> Dict

This is the only function the backend needs to call.

------------------------------------------------------------------------

# Input Contract

## Inventory Payload

Minimal required fields:

\[ { "name": "Eggs", "expiration_date": "2026-02-12" }\]

Optional fields: - category - purchase_date - quantity

Inventory names are canonicalized internally.

## Restrictions

Example:

\["allergy_nuts", "diet_vegan"\]

Defined in: config/restrictions.json

Restrictions are strictly enforced before scoring.

------------------------------------------------------------------------

# Output Contract

{ "mode": "low_stock", "inventory_summary": { "unique_items_count": 6,
"expiring_soon_count": 3, "expiring_soon_items": \["egg", "milk",
"spinach"\] }, "recommendations": \[...\], "shopping_list": \[...\],
"debug": {} }

------------------------------------------------------------------------

# Mode Logic

Modes: - empty_fridge - low_stock - abundant

Defined in config/policy.json.

Modes control: - candidate thresholds - scoring behavior - quick-bites
cap - shopping list inclusion

------------------------------------------------------------------------

# Restriction Handling

Restrictions: - Are hard filters - Remove recipes before scoring - Also
filter shopping list suggestions

Defined in config/restrictions.json.

------------------------------------------------------------------------

# Canonicalization

Ingredient normalization includes: - Multi-word phrase preservation -
Alias mapping - Drop token filtering

Located in core/canonicalizer.py.

------------------------------------------------------------------------

# Policy-Driven Behavior

All scoring and thresholds configurable in: config/policy.json

Editable parameters: - min_matched_core per mode - max_missing_core per
mode - scoring weights - quick-bites cap - diversity limits

------------------------------------------------------------------------

# Shopping List Logic

For low_stock or empty_fridge: - Aggregates missing ingredients across
near-miss candidates - Filters vague tokens - Filters restricted
ingredients - Returns top unlock-value ingredients

Located in core/shopping_list.py.

------------------------------------------------------------------------

# Debug Mode

Set debug=True to return: - exclusion counts - scored candidate count -
quick-bites cap - duplicate detection - inventory canonical set

------------------------------------------------------------------------

# How to Run Locally

python run_local.py

------------------------------------------------------------------------

# Environment Variables

Create a local `.env` file (do not commit it) based on `.env.example`:

```
FATSECRET_CLIENT_ID="..."
FATSECRET_CLIENT_SECRET="..."
```

------------------------------------------------------------------------

# Deploy on Render

This service can be deployed as a Render web service.

1) Push this repo to GitHub.
2) In Render, create a **Web Service** from the repo.
3) Build command:

```
pip install -r requirements.txt
```

4) Start command:

```
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

5) Set environment variables in Render:

- `FATSECRET_CLIENT_ID` (optional)
- `FATSECRET_CLIENT_SECRET` (optional)

Once deployed, set `RECOMMENDER_URL` in `foodies` to:

```
https://<your-render-service>.onrender.com/recommend
```

-----------------------------------------------------------------------

# Known Limitations

Not yet implemented: - Minimum coverage floor per mode - Ingredient-type
weighted scoring - Staple de-prioritization - Semantic ingredient
hierarchy

------------------------------------------------------------------------

# Integration Notes

Option A -- Import directly: from core.engine import recommend

Option B -- Wrap in API endpoint.

Important: - Cache df_parsed.csv in memory on service startup. - Do not
reload dataset per request.

------------------------------------------------------------------------

# Current Stability

✔ Deterministic\
✔ Restriction-safe\
✔ Config-driven\
✔ Diversity-safe\
✔ Shopping list integrated

This module is stable for backend integration.
