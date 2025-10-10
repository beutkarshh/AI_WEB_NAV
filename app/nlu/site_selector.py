"""
AI-Powered Site Selection Module
Uses Ollama to intelligently decide which e-commerce sites to visit based on product category analysis
"""

from app.nlu.llm_client import ollama_chat
import json
from typing import List, Dict

def select_optimal_sites(intent: dict, query: str) -> List[str]:
    """
    Use Ollama to intelligently select which e-commerce sites to use based on the product category and query
    
    Returns: List of site names to use (e.g., ['amazon', 'flipkart'] or ['amazon', 'flipkart', 'myntra'])
    """
    try:
        category = intent.get("category", "product")
        brands = intent.get("brands", [])
        features = intent.get("features", [])
        budget = intent.get("max_price")
        
        # Create detailed prompt for site selection
        prompt = f"""You are an expert e-commerce consultant for Indian markets. Analyze this shopping query and decide which platforms will give the best results.

QUERY: "{query}"
PARSED INTENT:
- Category: {category}
- Brands: {", ".join(brands) if brands else "none specified"}
- Features: {", ".join(features) if features else "none specified"}
- Budget: ₹{budget:,} if budget else "no limit specified"

AVAILABLE PLATFORMS:
1. AMAZON - Best for: Electronics, gadgets, books, general products, international brands, tech accessories
2. FLIPKART - Best for: Electronics, smartphones, home appliances, competitive prices, exclusive launches
3. MYNTRA - Best for: Fashion, clothing, footwear, accessories, personal care, beauty products, lifestyle items

SELECTION RULES:
- For ELECTRONICS/TECH: Always include Amazon + Flipkart (best selection and pricing)  
- For FASHION/LIFESTYLE: Include Amazon + Flipkart + Myntra (Myntra has exclusive fashion brands)
- For BOOKS/MEDIA: Primarily Amazon (best selection)
- For HOME/KITCHEN: Amazon + Flipkart (good variety and pricing)
- For BEAUTY/PERSONAL CARE: Amazon + Myntra (Myntra has exclusive beauty brands)

FASHION KEYWORDS: clothing, clothes, shirt, t-shirt, jeans, dress, saree, kurta, footwear, shoes, sneakers, sandals, boots, heels, accessories, watch, bag, handbag, jewelry, sunglasses, personal care, skincare, cosmetics, perfume, grooming, fashion, style, wear

ANALYSIS REQUIRED:
1. What product category is this query about?
2. Which platforms have the best selection for this category?
3. Are there any specific brand advantages on certain platforms?

OUTPUT FORMAT:
Return ONLY a JSON array of platform names to use. Examples:
["amazon", "flipkart"] - for electronics
["amazon", "flipkart", "myntra"] - for fashion
["amazon"] - for books only

Analyze the query and return the optimal platform selection:"""

        messages = [{"role": "user", "content": prompt}]
        response = ollama_chat(messages, temperature=0.1).strip()
        
        # Clean up and parse the response
        response = response.strip('`"\' \n')
        if response.startswith('json'):
            response = response[4:].strip()
        
        try:
            sites = json.loads(response)
            if isinstance(sites, list) and all(isinstance(s, str) for s in sites):
                # Validate site names
                valid_sites = []
                for site in sites:
                    if site.lower() in ['amazon', 'flipkart', 'myntra']:
                        valid_sites.append(site.lower())
                
                if valid_sites:
                    print(f"[ai] Site selection: {valid_sites} (reason: {category} category)")
                    return valid_sites
        except json.JSONDecodeError:
            pass
        
        # If parsing fails, extract site names from text
        response_lower = response.lower()
        fallback_sites = []
        if 'amazon' in response_lower:
            fallback_sites.append('amazon')
        if 'flipkart' in response_lower:
            fallback_sites.append('flipkart')  
        if 'myntra' in response_lower:
            fallback_sites.append('myntra')
            
        if fallback_sites:
            print(f"[ai] Site selection (parsed): {fallback_sites}")
            return fallback_sites
            
    except Exception as e:
        print(f"[warning] AI site selection failed: {e}")
    
    # Fallback to rule-based selection
    return _rule_based_site_selection(intent, query)

def _rule_based_site_selection(intent: dict, query: str) -> List[str]:
    """
    Fallback rule-based site selection if AI fails
    """
    category = intent.get("category", "product").lower()
    query_text = (query + " " + str(intent)).lower()
    
    # Fashion keywords detection
    fashion_keywords = {
        "clothing", "clothes", "shirt", "t-shirt", "jeans", "dress", "saree", "kurta",
        "footwear", "shoes", "sneakers", "sandals", "boots", "heels", 
        "accessories", "watch", "bag", "handbag", "jewelry", "sunglasses",
        "personal care", "skincare", "cosmetics", "perfume", "grooming",
        "fashion", "style", "wear", "casual", "formal", "ethnic"
    }
    
    is_fashion = any(keyword in query_text for keyword in fashion_keywords)
    
    if is_fashion:
        print("[fallback] Fashion detected -> Amazon + Flipkart + Myntra")
        return ['amazon', 'flipkart', 'myntra']
    else:
        print("[fallback] General/Electronics -> Amazon + Flipkart")
        return ['amazon', 'flipkart']

def get_site_reasoning(query: str, selected_sites: List[str]) -> str:
    """
    Generate a brief explanation of why these sites were selected
    """
    if len(selected_sites) == 3:
        return f"Fashion/lifestyle query detected - using all platforms for best selection"
    elif 'myntra' not in selected_sites:
        return f"Electronics/general query - using Amazon & Flipkart for competitive pricing"
    else:
        return f"Mixed category - optimized platform selection"