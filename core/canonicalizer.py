import re

# ---- Multi-word phrases to preserve (expand over time) ----
PHRASE_INGREDIENTS = [
    # spices / blends
    "chinese five spice",
    "five spice",
    "curry powder",
    "chili powder",
    "black pepper",
    "sea salt",

    # oils / condiments
    "olive oil",
    "sesame oil",
    "soy sauce",
    "fish sauce",
    "oyster sauce",

    # stocks
    "chicken stock",
    "beef stock",
    "vegetable stock",
    "fish stock",

    # produce / common phrases
    "spring onion",
    "green onion",
    "sweet potato",
    "bell pepper",
    "russet potato",

    # dairy / cheese / plant milk
    "parmesan cheese",
    "cheddar cheese",
    "cream cheese",
    "coconut milk",
    "evaporated milk",
    "evaporated milk",
    "whole milk",
    "skim milk",
    "almond milk",

    # proteins / cuts
    "chicken breast",
    "chicken thigh",
    "pork belly",
    "beef brisket",
]

# ---- Alias map (canonical forms) ----
ALIASES = {
    "extra virgin olive oil": "olive oil",
    "vegetable oil": "oil",
    "canola oil": "oil",

    # plurals
    "eggs": "egg",
    "tomatoes": "tomato",
    "onions": "onion",
    "potatoes": "potato",
    "russet potatoes": "russet potato"

    # normalize stocks
    "chicken stock": "stock",
    "beef stock": "stock",
    "vegetable stock": "stock",
    "fish stock": "stock",

    # IMPORTANT: keep coconut milk distinct from milk
    "coconut milk": "coconut milk",

    # parts of ingredient
    "yolk": "egg",
    "egg yolk": "egg",

    # normalize spice blends
    "chinese five spice": "five spice",
}

# tokens that are usually not meaningful alone in this dataset
DROP_TOKENS = {
    "five", "chinese",
    "t", "reduced", "eating", "single", "back", "flower",
    "fresh", "large", "small"
}


def canonicalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def stable_dedupe(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def parse_ingredients(text: str):
    """
    Phrase-aware parsing of ingredient string.
    Returns list of canonical ingredient tokens (stable order).
    """
    text = canonicalize_text(text)
    found = []

    # Longest phrases first (important!)
    for phrase in sorted(PHRASE_INGREDIENTS, key=len, reverse=True):
        if phrase in text:
            found.append(phrase)
            text = text.replace(phrase, " ")

    tokens = [t for t in text.split() if t and t not in DROP_TOKENS]

    all_items = found + tokens

    # Apply alias map after phrase extraction
    normalized = [ALIASES.get(item, item) for item in all_items]

    # Stable dedupe
    return stable_dedupe(normalized)