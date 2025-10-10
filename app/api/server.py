from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
import asyncio
import sys
import os

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import run
from app.wiki.api import wiki_router

app = FastAPI(
    title="AI Web Navigator", 
    description="E-commerce product search with deep scraping + Wikipedia long-running tasks",
    version="2.0.0"
)

# Include Wikipedia API routes
app.include_router(wiki_router)

class SearchRequest(BaseModel):
    query: str
    mode: Optional[str] = "quick"  # "quick" or "deep"
    max_pages: Optional[int] = 7

@app.get("/health")
def health():
    return {"status": "ok", "message": "AI Web Navigator is running"}

@app.post("/search")
async def search_products(request: SearchRequest):
    """
    Search for products across e-commerce sites
    
    - **query**: Product search query (e.g., "watches under 5000")
    - **mode**: Search mode - "quick" (first page only) or "deep" (multiple pages)
    - **max_pages**: Maximum pages per site for deep search (default: 3)
    """
    try:
        # Run the main search pipeline
        result = await asyncio.to_thread(
            run, 
            request.query, 
            mode=request.mode, 
            max_pages=request.max_pages
        )
        
        return {
            "status": "success",
            "query": request.query,
            "mode": request.mode,
            "max_pages": request.max_pages if request.mode == "deep" else 1,
            "items_found": len(result) if result else 0,
            "results": result[:20] if result else []  # Return top 20 results
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "query": request.query
        }

@app.get("/search")  
async def search_products_get(
    query: str = Query(..., description="Product search query"),
    mode: str = Query("quick", description="Search mode: quick or deep"),
    max_pages: int = Query(7, description="Max pages for deep search")
):
    """GET endpoint for product search - same as POST but via URL parameters"""
    request = SearchRequest(query=query, mode=mode, max_pages=max_pages)
    return await search_products(request)

# Legacy endpoint
@app.post("/run")
def run_legacy():
    return {"result": "Use /search endpoint instead", "status": "deprecated"}
