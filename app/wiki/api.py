"""
Wikipedia Movie Scraper API
RESTful API endpoints for managing long-running Wikipedia scraping jobs
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.wiki.orchestrator import orchestrator

# Create API router for wiki endpoints
wiki_router = APIRouter(prefix="/wiki", tags=["Wikipedia"])

class CreateJobRequest(BaseModel):
    description: Optional[str] = "Collect movies from Wikipedia"
    years_back: int = 20
    shard_size: int = 100
    start_immediately: bool = True

class JobResponse(BaseModel):
    job_id: str
    status: str
    description: str
    created_at: str
    items_total: int = 0
    items_processed: int = 0
    items_failed: int = 0
    progress_percent: float = 0.0
    current_year: Optional[int] = None
    data_folder: Optional[str] = None

@wiki_router.post("/jobs", response_model=Dict[str, str])
async def create_movie_job(request: CreateJobRequest):
    """
    Create a new Wikipedia movie collection job
    
    This starts a long-running task that will:
    1. Discover all movies from Wikipedia category pages
    2. Scrape individual movie pages for detailed information
    3. Save results to JSONL files and database
    
    The job runs in the background and can take hours to complete.
    """
    try:
        job_id = orchestrator.start_movie_collection_job(
            description=request.description or f"Collect movies from last {request.years_back} years",
            years_back=request.years_back,
            shard_size=request.shard_size,
            start_immediately=request.start_immediately
        )
        
        return {
            "job_id": job_id,
            "status": "created",
            "message": f"Movie collection job created for last {request.years_back} years"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@wiki_router.post("/jobs/{job_id}/start")
async def start_job(job_id: str):
    """Start a queued job"""
    success = orchestrator.start_job_processing(job_id)
    
    if success:
        return {"job_id": job_id, "status": "started", "message": "Job started successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to start job (may already be running)")

@wiki_router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs():
    """List all Wikipedia scraping jobs"""
    try:
        jobs = orchestrator.list_all_jobs()
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

@wiki_router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get detailed status of a specific job"""
    job_data = orchestrator.get_job_progress(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return JobResponse(**job_data)

@wiki_router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str, 
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """
    Get results from a completed job
    
    Returns movie data that was scraped and saved to the database.
    """
    try:
        results = orchestrator.get_job_results(job_id, limit)
        
        return {
            "job_id": job_id,
            "count": len(results),
            "limit": limit,
            "offset": offset,
            "movies": results
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@wiki_router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running job (limited support)"""
    success = orchestrator.pause_job(job_id)
    
    if success:
        return {"job_id": job_id, "status": "paused", "message": "Job paused (current operations will complete)"}
    else:
        raise HTTPException(status_code=400, detail="Failed to pause job (may not be running)")

@wiki_router.get("/jobs/{job_id}/download/{file_type}")
async def download_results(job_id: str, file_type: str):
    """
    Download job results in different formats
    
    file_type: 'json' or 'jsonl'
    """
    if file_type not in ['json', 'jsonl']:
        raise HTTPException(status_code=400, detail="file_type must be 'json' or 'jsonl'")
    
    job_data = orchestrator.get_job_progress(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    # This would implement actual file download
    # For now, return a message about where to find the files
    data_folder = job_data.get('data_folder', 'Unknown')
    
    return {
        "job_id": job_id,
        "file_type": file_type,
        "message": f"Results available in: {data_folder}",
        "note": "Download functionality would be implemented here"
    }

# Health check for wiki system
@wiki_router.get("/health")
async def wiki_health_check():
    """Health check for Wikipedia scraping system"""
    try:
        # Test database connection
        jobs = orchestrator.list_all_jobs()
        
        return {
            "status": "healthy",
            "system": "wikipedia_scraper",
            "timestamp": datetime.now().isoformat(),
            "total_jobs": len(jobs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System unhealthy: {str(e)}")

# Example usage documentation
@wiki_router.get("/docs/examples")
async def api_examples():
    """API usage examples"""
    return {
        "title": "Wikipedia Movie Scraper API Examples",
        "examples": {
            "create_job": {
                "method": "POST",
                "url": "/wiki/jobs",
                "body": {
                    "description": "Collect all movies from last 20 years",
                    "years_back": 20,
                    "shard_size": 100,
                    "start_immediately": True
                }
            },
            "check_status": {
                "method": "GET",
                "url": "/wiki/jobs/{job_id}"
            },
            "get_results": {
                "method": "GET", 
                "url": "/wiki/jobs/{job_id}/results?limit=50"
            },
            "list_all_jobs": {
                "method": "GET",
                "url": "/wiki/jobs"
            }
        },
        "workflow": [
            "1. Create a job with POST /wiki/jobs",
            "2. Monitor progress with GET /wiki/jobs/{job_id}",
            "3. When completed, get results with GET /wiki/jobs/{job_id}/results",
            "4. Download files from the data_folder location"
        ]
    }