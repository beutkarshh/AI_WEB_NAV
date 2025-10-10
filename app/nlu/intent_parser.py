import json
from .llm_client import ollama_chat

SYSTEM = (
  "You convert a shopping request into strict JSON with keys: "
  "category (string), max_price (int or null), brands (array of strings), "
  "features (array of strings). Output JSON only."
)

def parse_intent(user_text: str) -> dict:
    out = ollama_chat([
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": f"Text: {user_text}\nReturn JSON only."}
    ])

    # guard: extract JSON if model adds extra text
    start, end = out.find("{"), out.rfind("}")
    if start >= 0 and end > start:
        out = out[start:end+1]
    try:
        intent = json.loads(out)
    except Exception:
        # ultra-robust fallback (keeps app running)
        q = user_text.lower()
        cat = "smartphone" if "phone" in q else "laptop" if "laptop" in q else "product"
        return {"category": cat, "max_price": None, "brands": [], "features": []}
    # normalize some fields
    intent.setdefault("brands", [])
    intent.setdefault("features", [])
    return intent
