# app/main.py
import sys, time, json
from pathlib import Path

# --- DB & repos ---
from app.utils.db import init_db
from app.utils.repo import create_run, upsert_site, insert_item
from app.utils.hashing import item_hash

# --- IO / pipeline pieces ---
from app.output.render_table import print_table
from app.plan.planner import build_plan
from app.browse.executor import run_sites
from app.extract.extractor import extract_items
from app.normalize.price_parser import parse_inr
from app.normalize.rating_parser import parse_rating
from app.normalize.title_normalizer import normalize_title
from app.normalize.brand_infer import infer_brand

# --- Optional cache (will be None if the module doesn't exist yet) ---
try:
    from app.failover.cache_manager import cache_lookup, cache_store
except Exception:
    cache_lookup = cache_store = None  # caching not available yet

ART_DIR = Path("data/artifacts")
ART_DIR.mkdir(parents=True, exist_ok=True)


def new_run_id() -> str:
    return f"run_{int(time.time())}"


# -------- Intent parsing --------
def _rule_based_intent(query: str) -> dict:
    q = query.lower()
    cat = "smartphone" if "phone" in q else "laptop" if "laptop" in q else "product"
    brands = [
        b for b in [
            "samsung","redmi","apple","oneplus","vivo",
            "oppo","realme","motorola","hp","lenovo","asus","dell"
        ] if b in q
    ]
    feats = []
    if "5g" in q: feats.append("5g")
    if "5000" in q or "mah" in q: feats.append("5000mah")
    max_price = None
    for tok in q.replace("₹", "").replace(",", "").split():
        if tok.endswith("k") and tok[:-1].isdigit():
            max_price = int(tok[:-1]) * 1000
        elif tok.isdigit():
            max_price = int(tok)
    return {"category": cat, "brands": brands, "features": feats, "max_price": max_price}


def _ollama_intent_or_fallback(user_text: str) -> dict:
    """
    Try Ollama-based intent parsing. If anything fails, fall back to rule-based.
    """
    try:
        from app.nlu.intent_parser import parse_intent  # your Ollama-backed parser
        intent = parse_intent(user_text)
        # normalize safe defaults
        intent.setdefault("brands", [])
        intent.setdefault("features", [])
        return intent
    except Exception:
        return _rule_based_intent(user_text)


# -------- Main pipeline --------
def run(user_query: str, use_cache: bool = True):
    init_db()

    # 1) Intent (Ollama if available)
    intent = _ollama_intent_or_fallback(user_query)
    # Add original query for AI site selection
    intent["query"] = user_query

    # 2) Optional: Query cache (instant for repeat demos)
    if use_cache and cache_lookup is not None:
        hit = cache_lookup(intent)
        if hit:
            # If you stored full results, you might have hit["top5"] or hit["results"]
            top5 = hit.get("top5") or hit.get("results", [])[:5]
            print("[CACHE] Instant response")
            print_table(top5)
            return

    # 3) Plan sites
    plan = build_plan(intent)

    # 4) Create run
    run_id = new_run_id()
    create_run(run_id, user_query, sites_total=len(plan.get("sites", [])))

    pw = browser = ctx = None
    try:
        # 5) Execute (open tabs, wait)
        pw, browser, ctx, pages = run_sites(plan)

        # 6) Extract raw items
        raw = extract_items(pages)

        # 7) Normalize + validate + dedup + budget filter + DB insert
        rows, seen = [], set()
        filtered_count = 0
        budget_filtered = 0
        max_price = intent.get("max_price")
        
        for r in raw:
            price = parse_inr(r.get("price_txt"))
            title = r.get("title", "")
            if not title or price <= 0:
                filtered_count += 1
                continue
            
            # Apply budget filter if specified
            if max_price and price > max_price:
                budget_filtered += 1
                continue

            tnorm = normalize_title(title)
            brand = infer_brand(tnorm)
            key = (r["site"], tnorm, price)
            if key in seen:
                continue
            seen.add(key)

            row = {
                "site": r["site"],
                "title": title,
                "title_norm": tnorm,
                "brand": brand,
                "price_inr": price,
                "rating": parse_rating(r.get("rating_txt")),
                "url": r.get("url"),
            }
            rows.append(row)

            site_id = upsert_site(r["site"])
            insert_item(
                run_id,
                site_id,
                title,
                tnorm,
                brand,
                price,
                row["rating"],
                row["url"],
                item_hash(r["site"], tnorm, price),
            )

        budget_msg = f", Budget filtered (>{max_price}): {budget_filtered}" if max_price else ""
        print(f"[debug] Raw items: {len(raw)}, Filtered out: {filtered_count}{budget_msg}, Valid rows: {len(rows)}")

        # 8) Multi-site ranking: get top 5 from each site
        sites = {}
        for row in rows:
            site_name = row["site"]
            if site_name not in sites:
                sites[site_name] = []
            sites[site_name].append(row)
        
        # Sort each site's results from high price to low price
        top_results = []
        for site_name, site_rows in sites.items():
            # Sort by: rating desc (primary), then price desc (high to low)
            site_rows.sort(key=lambda x: (-(x["rating"]), -(x["price_inr"])))
            
            top_site_results = site_rows[:5]  # Top 5 from each site
            top_results.extend(top_site_results)
            print(f"[{site_name}] Found {len(site_rows)} items, showing top {len(top_site_results)}")
        
        # Sort combined results by rating desc, then price desc (high to low)
        top_results.sort(key=lambda x: (-(x["rating"]), -(x["price_inr"])))
        print_table(top_results)

        # 9) Optional: write minimal artifacts + populate cache
        # Write JSON artifacts locally regardless (handy for inspection)
        results_path = ART_DIR / "results_latest.json"
        top5_path = ART_DIR / "top5_latest.json"
        with results_path.open("w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)
        with top5_path.open("w", encoding="utf-8") as f:
            json.dump(top_results, f, ensure_ascii=False)

        # If cache manager exists, store artifacts under a fingerprinted name
        if use_cache and cache_store is not None:
            # We'll pass explicit paths so the cache index knows where they live
            # CSV path is optional here; pass an empty string if you don't write CSV yet
            cache_store(
                intent=intent,
                run_id=run_id,
                results=rows,
                top5=top_results,
                csv_path=str(ART_DIR / "results_latest.csv"),  # fill later if/when you export CSV
                res_path=str(results_path),
                top5_path=str(top5_path),
                ttl_sec=0  # 0 => treat as non-expiring for demo; change later if you want
            )

    finally:
        # 10) Clean up Playwright
        try:
            if ctx: ctx.close()
        except Exception:
            pass
        try:
            if browser: browser.close()
        except Exception:
            pass
        try:
            if pw: pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "phones under 20000 5g samsung")
