import json, urllib.parse
from pathlib import Path
def build_plan(intent:dict)->dict:
    prof = json.loads(Path("app/plan/site_profiles/amazon.json").read_text(encoding="utf-8"))
    q = intent.get("category","") + " " + " ".join(intent.get("features",[])) + " " + " ".join(intent.get("brands",[]))
    q = q.strip() or "smartphone"
    prof["search_url"] = prof["search_url"].format(query=urllib.parse.quote_plus(q))
    return {"sites":[prof]}
