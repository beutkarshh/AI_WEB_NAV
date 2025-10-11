"""
Wikipedia Movie Scraper API
RESTful API endpoints for managing long-running Wikipedia scraping jobs
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io
from pathlib import Path

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

@wiki_router.get("/jobs/demo/download/{file_type}")
async def download_demo_results(file_type: str):
    """
    Download demo results in different formats for testing
    
    file_type: 'json', 'jsonl', or 'csv'
    """
    if file_type not in ['json', 'jsonl', 'csv']:
        raise HTTPException(status_code=400, detail="file_type must be 'json', 'jsonl', or 'csv'")
    
    try:
        # Load sample data
        sample_file = Path("data/sample_wikipedia_movies.json")
        if not sample_file.exists():
            raise HTTPException(status_code=404, detail="Sample data not found")
        
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        results = sample_data.get('movies', [])
        
        if not results:
            raise HTTPException(status_code=404, detail="No sample results found")
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_movies_demo_{timestamp}.{file_type}"
        
        if file_type == 'json':
            # Create JSON file
            json_data = {
                "job_id": "demo_wikipedia_movies",
                "description": "Demo Wikipedia Movies Collection (Last 20 Years)",
                "created_at": datetime.now().isoformat(),
                "total_movies": len(results),
                "movies": results
            }
            
            # Create temporary file
            temp_file = Path(f"/tmp/{filename}")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            return FileResponse(
                temp_file,
                media_type='application/json',
                filename=filename
            )
            
        elif file_type == 'csv':
            # Create CSV file
            temp_file = Path(f"/tmp/{filename}")
            
            with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                if results:
                    # Get all possible fields from the first result
                    fieldnames = set()
                    for movie in results:
                        if isinstance(movie.get('raw_data'), dict):
                            fieldnames.update(movie['raw_data'].keys())
                    
                    # Standard fields
                    fieldnames.update(['id', 'url', 'title', 'year', 'shard_file'])
                    fieldnames = sorted(list(fieldnames))
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for movie in results:
                        row = {
                            'id': movie.get('id'),
                            'url': movie.get('url'),
                            'title': movie.get('title'),
                            'year': movie.get('year'),
                            'shard_file': movie.get('shard_file')
                        }
                        
                        # Add raw data fields
                        if isinstance(movie.get('raw_data'), dict):
                            row.update(movie['raw_data'])
                        
                        writer.writerow(row)
            
            return FileResponse(
                temp_file,
                media_type='text/csv',
                filename=filename
            )
            
        else:  # jsonl
            # Create JSONL file
            temp_file = Path(f"/tmp/{filename}")
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                for movie in results:
                    json.dump(movie, f, ensure_ascii=False)
                    f.write('\n')
            
            return FileResponse(
                temp_file,
                media_type='application/x-jsonlines',
                filename=filename
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create demo download file: {str(e)}")

@wiki_router.get("/jobs/{job_id}/download/{file_type}")
async def download_results(job_id: str, file_type: str):
    """
    Download job results in different formats
    
    file_type: 'json', 'jsonl', or 'csv'
    """
    if file_type not in ['json', 'jsonl', 'csv']:
        raise HTTPException(status_code=400, detail="file_type must be 'json', 'jsonl', or 'csv'")
    
    job_data = orchestrator.get_job_progress(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job_data.get('status') != 'completed':
        raise HTTPException(status_code=400, detail="Job must be completed to download results")
    
    try:
        # Get all results for this job
        results = orchestrator.get_job_results(job_id, limit=10000)  # Get up to 10k results
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this job")
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_movies_{job_id}_{timestamp}.{file_type}"
        
        if file_type == 'json':
            # Create JSON file
            json_data = {
                "job_id": job_id,
                "description": job_data.get('description', ''),
                "created_at": job_data.get('created_at', ''),
                "total_movies": len(results),
                "movies": results
            }
            
            # Create temporary file
            temp_file = Path(f"/tmp/{filename}")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            return FileResponse(
                temp_file,
                media_type='application/json',
                filename=filename
            )
            
        elif file_type == 'csv':
            # Create CSV file
            temp_file = Path(f"/tmp/{filename}")
            
            with open(temp_file, 'w', newline='', encoding='utf-8') as f:
                if results:
                    # Get all possible fields from the first result
                    fieldnames = set()
                    for movie in results:
                        if isinstance(movie.get('raw_data'), dict):
                            fieldnames.update(movie['raw_data'].keys())
                    
                    # Standard fields
                    fieldnames.update(['id', 'url', 'title', 'year', 'shard_file'])
                    fieldnames = sorted(list(fieldnames))
                    
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for movie in results:
                        row = {
                            'id': movie.get('id'),
                            'url': movie.get('url'),
                            'title': movie.get('title'),
                            'year': movie.get('year'),
                            'shard_file': movie.get('shard_file')
                        }
                        
                        # Add raw data fields
                        if isinstance(movie.get('raw_data'), dict):
                            row.update(movie['raw_data'])
                        
                        writer.writerow(row)
            
            return FileResponse(
                temp_file,
                media_type='text/csv',
                filename=filename
            )
            
        else:  # jsonl
            # Create JSONL file
            temp_file = Path(f"/tmp/{filename}")
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                for movie in results:
                    json.dump(movie, f, ensure_ascii=False)
                    f.write('\n')
            
            return FileResponse(
                temp_file,
                media_type='application/x-jsonlines',
                filename=filename
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create download file: {str(e)}")

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