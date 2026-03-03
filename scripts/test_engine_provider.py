# scripts/test_engine_provider.py
import json
from core.engine import recommend
from dotenv import load_dotenv

load_dotenv()

# Adjust inventory to your schema
inventory_payload = [
    {"name": "milk", "expiration_date": "2026-02-26", "category": "dairy"},
    {"name": "egg", "expiration_date": "2026-02-26", "category": "protein"},
    {"name": "spinach", "expiration_date": "2026-02-26", "category": "produce"},
    {"name": "onion", "expiration_date": "2026-03-02", "category": "produce"},
    {"name": "garlic", "expiration_date": "2026-03-05", "category": "produce"},
    {"name": "olive oil", "expiration_date": "2026-04-01", "category": "pantry"},
]

restrictions = ["allergy_nuts"]

resp = recommend(
    inventory_payload=inventory_payload,
    restrictions=restrictions,
    top_k=5,
    debug=True,
    provider_enabled=True,
)

print(json.dumps(resp, indent=2)[:5000])