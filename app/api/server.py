from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
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

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:8081", "http://127.0.0.1:8081", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include Wikipedia API routes
app.include_router(wiki_router)

class SearchRequest(BaseModel):
    query: str
    mode: Optional[str] = "quick"  # "quick" or "deep"
    max_pages: Optional[int] = 7
    max_price: Optional[float] = None
    sites: Optional[List[str]] = None
    k: Optional[int] = 20
    category_hint: Optional[str] = None

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

# API endpoints that frontend expects
@app.post("/api/search")
async def api_search_products(request: SearchRequest):
    """
    API endpoint for product search - matches frontend expectations
    """
    try:
        # Run the main search pipeline
        result = await asyncio.to_thread(
            run, 
            request.query, 
            mode=request.mode, 
            max_pages=request.max_pages
        )
        
        # Transform results to match frontend expectations
        transformed_results = []
        if result and "items" in result:
            items = result["items"]
            for item in items[:request.k or 20]:
                # Extract specifications from title (basic parsing)
                title = item.get("title", "Unknown Product")
                specifications = []
                if "RAM" in title:
                    ram_match = title.split("RAM")[0].split()[-1] + " RAM"
                    specifications.append(ram_match)
                if "SSD" in title:
                    ssd_match = title.split("SSD")[0].split()[-1] + " SSD"
                    specifications.append(ssd_match)
                if "Intel" in title or "AMD" in title:
                    cpu_match = title.split("Intel")[1].split()[0:3] if "Intel" in title else title.split("AMD")[1].split()[0:3]
                    specifications.append(" ".join(cpu_match))
                
                transformed_results.append({
                    "name": title,
                    "price": str(item.get("price_inr", 0)),
                    "rating": float(item.get("rating", 0)),
                    "specifications": specifications[:3],  # Limit to 3 specs
                    "link": item.get("url", ""),
                    "image": "",  # Images not available in current scraping
                    "source": item.get("site", "Unknown"),
                    "category": "Electronics",  # Default category
                    "review_count": 0,  # Review count not available in current scraping
                    "is_cheapest": False  # Could be calculated based on price comparison
                })
        
        return {
            "status": "success",
            "query": request.query,
            "results": transformed_results,
            "summary": f"Found {len(transformed_results)} products for '{request.query}'",
            "debug": {
                "raw_count": len(result) if result else 0,
                "sites": request.sites or ["amazon.in", "flipkart.com", "myntra.com"]
            }
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "query": request.query,
            "results": [],
            "summary": f"Error searching for '{request.query}'"
        }

@app.get("/api/providers")
def get_providers():
    """Get available e-commerce providers"""
    return {
        "providers": [
            {"id": "amazon.in", "name": "Amazon India", "enabled": True},
            {"id": "flipkart.com", "name": "Flipkart", "enabled": True},
            {"id": "myntra.com", "name": "Myntra", "enabled": True},
            {"id": "reliance.com", "name": "Reliance Digital", "enabled": True}
        ]
    }

@app.post("/api/compare")
async def compare_products(request: SearchRequest):
    """Compare products across different sites"""
    try:
        # Run search with comparison mode
        result = await asyncio.to_thread(
            run, 
            request.query, 
            mode="deep", 
            max_pages=3
        )
        
        # Transform results for comparison
        transformed_results = []
        if result and "items" in result:
            items = result["items"]
            for item in items[:10]:  # Limit for comparison
                # Extract specifications from title (basic parsing)
                title = item.get("title", "Unknown Product")
                specifications = []
                if "RAM" in title:
                    ram_match = title.split("RAM")[0].split()[-1] + " RAM"
                    specifications.append(ram_match)
                if "SSD" in title:
                    ssd_match = title.split("SSD")[0].split()[-1] + " SSD"
                    specifications.append(ssd_match)
                if "Intel" in title or "AMD" in title:
                    cpu_match = title.split("Intel")[1].split()[0:3] if "Intel" in title else title.split("AMD")[1].split()[0:3]
                    specifications.append(" ".join(cpu_match))
                
                transformed_results.append({
                    "name": title,
                    "price": str(item.get("price_inr", 0)),
                    "rating": float(item.get("rating", 0)),
                    "specifications": specifications[:3],  # Limit to 3 specs
                    "link": item.get("url", ""),
                    "image": "",  # Images not available in current scraping
                    "source": item.get("site", "Unknown"),
                    "category": "Electronics",  # Default category
                    "review_count": 0  # Review count not available in current scraping
                })
        
        return {
            "status": "success",
            "results": transformed_results,
            "summary": f"Comparison results for '{request.query}'",
            "total_count": len(transformed_results),
            "comparison_ready": len(transformed_results) >= 2
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "results": [],
            "summary": f"Error comparing products for '{request.query}'",
            "total_count": 0,
            "comparison_ready": False
        }

# Simple authentication endpoints for frontend compatibility
@app.options("/auth/login-json")
def login_options():
    from fastapi.responses import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.post("/auth/login-json")
def login_json(credentials: dict):
    """Simple login endpoint - accepts any email/password for demo"""
    email = credentials.get("email", "")
    password = credentials.get("password", "")
    
    # For demo purposes, accept any login
    if email and password:
        # Generate a simple token (in production, use proper JWT)
        import hashlib
        import time
        token_data = f"{email}:{int(time.time())}"
        token = hashlib.sha256(token_data.encode()).hexdigest()
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": "1",
                "email": email,
                "username": email.split("@")[0],
                "full_name": email.split("@")[0].title(),
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    else:
        return {"detail": "Email and password required"}, 400

@app.options("/auth/me")
def auth_me_options():
    from fastapi.responses import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.get("/auth/me")
def get_current_user():
    """Get current user info - returns demo user"""
    return {
        "id": "1",
        "email": "demo@example.com",
        "username": "demo",
        "full_name": "Demo User",
        "is_active": True,
        "is_verified": True,
        "created_at": "2024-01-01T00:00:00Z"
    }

@app.options("/auth/logout")
def logout_options():
    from fastapi.responses import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.post("/auth/logout")
def logout():
    """Simple logout endpoint"""
    return {"message": "Successfully logged out"}

@app.options("/auth/google-login")
def google_login_options():
    from fastapi.responses import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.post("/auth/google-login")
def google_login(google_data: dict):
    """Simple Google login endpoint for demo"""
    user_info = google_data.get("user_info", {})
    name = user_info.get("name", "Google User")
    email = user_info.get("email", "google@example.com")
    
    # Generate a simple token
    import hashlib
    import time
    token_data = f"{email}:{int(time.time())}"
    token = hashlib.sha256(token_data.encode()).hexdigest()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": "2",
            "email": email,
            "username": name.lower().replace(" ", "_"),
            "full_name": name,
            "is_active": True,
            "is_verified": True,
            "created_at": "2024-01-01T00:00:00Z"
        }
    }

# Legacy endpoint
@app.post("/run")
def run_legacy():
    return {"result": "Use /search endpoint instead", "status": "deprecated"}

# Serve React frontend as static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "frontend", "dist")

if os.path.exists(frontend_path):
    # Mount static files from the dist directory
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    
    # Serve specific static files
    @app.get("/favicon.ico")
    def serve_favicon():
        return FileResponse(os.path.join(frontend_path, "favicon.ico"))
    
    @app.get("/logo.png")
    def serve_logo():
        return FileResponse(os.path.join(frontend_path, "logo.png"))
    
    @app.get("/placeholder.svg")
    def serve_placeholder():
        return FileResponse(os.path.join(frontend_path, "placeholder.svg"))
    
    @app.get("/robots.txt")
    def serve_robots():
        return FileResponse(os.path.join(frontend_path, "robots.txt"))
    
    # Serve root route
    @app.get("/")
    def serve_root():
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return {"error": "Frontend index.html not found"}, 404
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{path:path}")
    def serve_frontend(path: str):
        # Don't serve API routes as static files
        if path.startswith("api/") or path.startswith("auth/") or path.startswith("wiki/") or path.startswith("health") or path.startswith("docs") or path.startswith("assets"):
            return {"error": "Not found"}, 404
        
        # Serve index.html for all other routes (SPA routing)
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            return {"error": "Frontend not built. Run 'npm run build' in frontend directory"}, 404
else:
    print(f"⚠️  Frontend build not found at {frontend_path}")
    print("   Run 'npm run build' in the frontend directory to enable static file serving")
