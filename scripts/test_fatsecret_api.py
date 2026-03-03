import os
import requests

TOKEN_URL = "https://oauth.fatsecret.com/connect/token"
BASE_REST = "https://platform.fatsecret.com/rest"

CLIENT_ID = os.getenv("FATSECRET_CLIENT_ID")
CLIENT_SECRET = os.getenv("FATSECRET_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Missing FATSECRET_CLIENT_ID / FATSECRET_CLIENT_SECRET env vars")

def get_token(scope: str = "basic") -> str:
    # OAuth2 client_credentials (per FatSecret docs)
    # Uses HTTP Basic auth with client_id:client_secret
    resp = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": scope},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]

def recipes_search_v3(token: str, query: str, max_results: int = 10, prep_time_to: int | None = None):
    url = f"{BASE_REST}/recipes/search/v3"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "format": "json",
        "search_expression": query,
        "max_results": max_results,
        "page_number": 0,
    }
    if prep_time_to is not None:
        params["prep_time.to"] = str(prep_time_to)

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"FatSecret error: {data['error']}")
    return data

def recipe_get_v2(token: str, recipe_id: str | int):
    # Details endpoint to get full recipe information (likely where instructions live)
    url = f"{BASE_REST}/recipe/v2"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"format": "json", "recipe_id": str(recipe_id)}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"FatSecret error: {data['error']}")
    return data

def main():
    token = get_token(scope="basic")
    print("✅ Token acquired")

    # 1) Search test
    search = recipes_search_v3(token, query="chicken", max_results=5, prep_time_to=None)
    print(search)
    print("✅ recipes.search.v3 ok")

    # Pull first recipe safely
    recipes = search.get("recipes", {}).get("recipe", [])
    if isinstance(recipes, dict):
        recipes = [recipes]
    if not recipes:
        print("No recipes returned.")
        return

    first = recipes[0]
    rid = first.get("recipe_id")
    print("\n--- First search result (key fields) ---")
    print("recipe_id:", rid)
    print("name:", first.get("recipe_name"))
    print("image:", first.get("recipe_image"))
    print("desc:", (first.get("recipe_description") or "")[:140])

    # Confirm nutrition + ingredients are present
    print("has_nutrition:", "recipe_nutrition" in first)
    print("has_ingredients:", "recipe_ingredients" in first)

    # 2) Detail test
    detail = recipe_get_v2(token, rid)
    print("\n✅ recipe.get.v2 ok")
    # Print likely instruction-related keys
    top_keys = list(detail.keys())
    print("detail top-level keys:", top_keys)

    # Try common places where instructions might appear
    # (we’ll inspect the returned JSON after you run it)
    print("\n--- detail sample (first 800 chars) ---")
    s = str(detail)
    print(s[:800])

if __name__ == "__main__":
    main()