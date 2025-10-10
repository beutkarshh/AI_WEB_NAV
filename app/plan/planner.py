import json, urllib.parse
from pathlib import Path
from app.nlu.query_optimizer import optimize_search_query
from app.nlu.site_selector import select_optimal_sites, get_site_reasoning

def build_plan(intent: dict, mode: str = "quick", max_pages: int = 1) -> dict:
    query = intent.get("query", "")
    
    # Use AI to intelligently select optimal sites for this query
    selected_sites = select_optimal_sites(intent, query)
    print(f"[ai] Site selection reasoning: {get_site_reasoning(query, selected_sites)}")
    
    # Display search mode info
    if mode == "deep":
        print(f"[🔍] Deep Search Mode: Scraping up to {max_pages} pages per site")
    else:
        print(f"[⚡] Quick Search Mode: Top 5 products from first page only")
    
    # Load site profiles for selected sites
    sites_to_use = []
    
    for site_name in selected_sites:
        try:
            site_prof = json.loads(Path(f"app/plan/site_profiles/{site_name}.json").read_text(encoding="utf-8"))
            
            # Configure pagination based on search mode
            if mode == "deep":
                site_prof["max_pages"] = max_pages
                site_prof["min_items_per_page"] = 20  # More items per page in deep mode
                print(f"[🔧] {site_name.title()}: Deep mode - {max_pages} pages")
            else:
                site_prof["max_pages"] = 1
                site_prof["min_items_per_page"] = 5   # Standard items in quick mode
                print(f"[🔧] {site_name.title()}: Quick mode - 1 page")
            
            sites_to_use.append((site_name, site_prof))
        except FileNotFoundError:
            print(f"[warning] Site profile not found: {site_name}.json - skipping")
            continue
    
    # Generate optimized queries for each selected site
    site_queries = {}
    
    try:
        # Use AI optimization for each platform
        for site_name, _ in sites_to_use:
            site_queries[site_name] = optimize_search_query(intent, site_name)
            print(f"[ai] {site_name.title()} optimized: '{site_queries[site_name]}'")
            
    except Exception as e:
        print(f"[warning] Falling back to rule-based queries: {e}")
        # Fallback to rule-based approach
        category = intent.get("category", "smartphone")
        brands = intent.get("brands", [])
        features = intent.get("features", [])
        
        base_query = category + " " + " ".join(features) + " " + " ".join(brands)
        base_query = base_query.strip() or "smartphone"
        
        for site_name, _ in sites_to_use:
            if site_name == "flipkart" and brands:
                # Brand-first strategy for Flipkart
                site_queries[site_name] = " ".join(brands) + " " + category + " " + " ".join(features)
            else:
                site_queries[site_name] = base_query
            site_queries[site_name] = site_queries[site_name].strip() or "smartphone"
    
    # Build site configurations with optimized URLs and price filtering
    max_price = intent.get("max_price")
    configured_sites = []
    
    for site_name, site_prof in sites_to_use:
        query = site_queries[site_name]
        
        # Build search URL
        search_url = site_prof["search_url"].format(query=urllib.parse.quote_plus(query))
        
        # Add price range filtering if budget specified
        if max_price:
            if site_name == "amazon":
                # Amazon price range format: &rh=p_36:min-max (in paise: 1 rupee = 100 paise)
                max_paise = max_price * 100
                search_url += f"&rh=p_36:0-{max_paise}"
            elif site_name == "flipkart":
                # Flipkart price range format: &p[]=facets.price_range.from=0&p[]=facets.price_range.to=max
                search_url += f"&p[]=facets.price_range.from=0&p[]=facets.price_range.to={max_price}"
            elif site_name == "myntra":
                # Myntra price filtering can be added here when implemented
                pass
        
        # Update site profile with final URL and store query for pagination
        site_prof["search_url"] = search_url
        site_prof["query"] = query  # Store the optimized query for pagination
        configured_sites.append(site_prof)
        
        # Debug output
        price_info = f" (max: ₹{max_price:,})" if max_price else ""
        print(f"[debug] {site_name.title()} query: '{query}'{price_info}")
    
    return {
        "mode": mode,
        "max_pages": max_pages,
        "sites": configured_sites,
        "metadata": {
            "search_mode": mode,
            "pages_per_site": max_pages if mode == "deep" else 1,
            "estimated_total_pages": len(configured_sites) * (max_pages if mode == "deep" else 1),
            "estimated_items": len(configured_sites) * (max_pages * 20 if mode == "deep" else 5),
            "query": query,
            "budget": max_price
        }
    }
