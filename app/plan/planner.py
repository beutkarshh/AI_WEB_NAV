import json, urllib.parse
from pathlib import Path
from app.nlu.query_optimizer import optimize_search_query

def build_plan(intent: dict) -> dict:
    # Load both Amazon and Flipkart profiles
    amazon_prof = json.loads(Path("app/plan/site_profiles/amazon.json").read_text(encoding="utf-8"))
    flipkart_prof = json.loads(Path("app/plan/site_profiles/flipkart.json").read_text(encoding="utf-8"))
    
    # Use Ollama to generate optimized search queries for each platform
    try:
        amazon_q = optimize_search_query(intent, "amazon")
        flipkart_q = optimize_search_query(intent, "flipkart")
    except Exception as e:
        print(f"[warning] Falling back to rule-based queries: {e}")
        # Fallback to rule-based approach
        category = intent.get("category", "smartphone")
        brands = intent.get("brands", [])
        features = intent.get("features", [])
        
        amazon_q = category + " " + " ".join(features) + " " + " ".join(brands)
        amazon_q = amazon_q.strip() or "smartphone"
        
        if brands:
            flipkart_q = " ".join(brands) + " " + category + " " + " ".join(features)
        else:
            flipkart_q = category + " " + " ".join(features)
        flipkart_q = flipkart_q.strip() or "smartphone"
    
    # Format search URLs with price range filters
    max_price = intent.get("max_price")
    
    # Amazon URL with price range
    amazon_url = amazon_prof["search_url"].format(query=urllib.parse.quote_plus(amazon_q))
    if max_price:
        # Amazon price range format: &rh=p_36:min-max (in paise: 1 rupee = 100 paise)
        max_paise = max_price * 100
        amazon_url += f"&rh=p_36:0-{max_paise}"
    amazon_prof["search_url"] = amazon_url
    
    # Flipkart URL with price range  
    flipkart_url = flipkart_prof["search_url"].format(query=urllib.parse.quote_plus(flipkart_q))
    if max_price:
        # Flipkart price range format: &p[]=facets.price_range.from=0&p[]=facets.price_range.to=max
        flipkart_url += f"&p[]=facets.price_range.from=0&p[]=facets.price_range.to={max_price}"
    flipkart_prof["search_url"] = flipkart_url
    
    print(f"[debug] Amazon query: '{amazon_q}' (max: ₹{max_price:,})" if max_price else f"[debug] Amazon query: '{amazon_q}'")
    print(f"[debug] Flipkart query: '{flipkart_q}' (max: ₹{max_price:,})" if max_price else f"[debug] Flipkart query: '{flipkart_q}'")
    
    return {"sites": [amazon_prof, flipkart_prof]}
