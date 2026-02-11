from core.engine import recommend

inventory_payload = [
    {"name": "Eggs", "expiration_date": "2026-02-12"},
    {"name": "Milk", "expiration_date": "2026-02-13"},
    {"name": "Spinach", "expiration_date": "2026-02-12"},
    {"name": "Olive oil"},
    {"name": "Onion"},
    {"name": "Garlic"},
]

resp = recommend(
    inventory_payload=inventory_payload,
    restrictions=["allergy_nuts"],
    top_k=8,
    debug=True
)

print("MODE:", resp["mode"])
print("SUMMARY:", resp["inventory_summary"])
print("\nTop recommendations:")
for i, r in enumerate(resp["recommendations"], 1):
    print(f"\n{i}. {r['title']}  (bucket={r['bucket']}, score={r['score']}, coverage={r['coverage']})")
    print("   matched:", r["matched"])
    print("   missing:", r["missing"][:10], "..." if len(r["missing"]) > 10 else "")
    print("   reasons:", r["reasons"])

print("\nDEBUG:", resp["debug"])

if "shopping_list" in resp:
    print("\nShopping list:")
    for x in resp["shopping_list"]:
        print("-", x)