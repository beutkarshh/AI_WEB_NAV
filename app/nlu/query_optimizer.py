from app.nlu.llm_client import ollama_chat

def optimize_search_query(intent: dict, platform: str) -> str:
    """
    Use Ollama to generate optimized search queries for specific platforms
    """
    try:
        category = intent.get("category", "product")
        brands = intent.get("brands", [])
        features = intent.get("features", [])
        max_price = intent.get("max_price")
        
        # Create context for the LLM
        user_context = {
            "category": category,
            "brands": brands,
            "features": features,
            "budget": max_price
        }
        
        platform_instructions = {
            "amazon": """
Amazon India search optimization rules:
- Use natural language queries
- Put category first, then brands: "smartphone samsung"
- Include specific features if mentioned
- Avoid price terms in search (filtering happens later)
- Examples: "laptop dell", "smartphone oneplus 5g", "headphones wireless bluetooth"
""",
            "flipkart": """
Flipkart India search optimization rules:
- Brand-first approach works better: "samsung smartphone" not "smartphone samsung"  
- Include quality/tier hints based on budget:
  - Budget >25000: add "premium" or "flagship"
  - Budget 15000-25000: add "mid-range" or "pro"
  - Budget <15000: use basic terms
- Flipkart responds well to specific model hints
- Examples: "samsung smartphone premium", "dell laptop business", "oneplus mobile flagship"
""",
            "myntra": """
Myntra fashion search optimization rules:
- Focus on fashion-specific terms: "men shirts", "women dress", "kids shoes"
- Include brand names prominently for fashion items
- Use style descriptors: "casual", "formal", "ethnic", "western"
- Be specific about clothing types: "kurta", "jeans", "saree", "sneakers"
- Add gender/age targeting: "men", "women", "boys", "girls"
- Examples: "levis jeans men", "zara dress women", "nike sneakers", "ethnic kurta men"
"""
        }
        
        prompt = f"""You are an expert at optimizing search queries for Indian e-commerce platforms.

Platform: {platform.upper()}
{platform_instructions.get(platform, "")}

User Intent:
- Category: {category}
- Brands: {", ".join(brands) if brands else "any"}
- Features: {", ".join(features) if features else "none specified"}
- Budget: ₹{max_price:,} if max_price else "no budget specified"

Generate the most effective search query for {platform} that will return relevant products matching the user's intent.

Requirements:
- Keep it concise (2-5 words)
- Focus on getting the right product category and brand
- Consider platform-specific search behavior
- Do NOT include price terms in the query

Return only the optimized search query, nothing else."""

        messages = [{"role": "user", "content": prompt}]
        optimized_query = ollama_chat(messages, temperature=0.1).strip()
        
        # Clean up the response (remove quotes, extra text)
        optimized_query = optimized_query.strip('"\'`')
        if '\n' in optimized_query:
            optimized_query = optimized_query.split('\n')[0]
            
        return optimized_query
        
    except Exception as e:
        print(f"[warning] Ollama query optimization failed: {e}")
        # Fallback to simple query construction
        if platform == "flipkart" and brands:
            return " ".join(brands) + " " + category
        else:
            return category + " " + " ".join(brands)