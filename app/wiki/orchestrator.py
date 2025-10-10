"""
Wikipedia Long-Running Task Orchestrator
Main system that coordinates movie scraping jobs
"""

import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from app.wiki.database import (
    init_wiki_db, create_wiki_job, update_job_status, get_job_status
)
from app.wiki.crawler import discover_movies_by_years
from app.wiki.scraper import MoviePageScraper

logger = logging.getLogger(__name__)

class WikiMovieTaskOrchestrator:
    def __init__(self):
        # Initialize database
        init_wiki_db()
        self.running_jobs = {}  # {job_id: thread}
    
    def start_movie_collection_job(
        self, 
        description: str = "Collect all movies from last 20 years",
        years_back: int = 20,
        shard_size: int = 100,
        start_immediately: bool = True
    ) -> str:
        """
        Start a long-running job to collect movies from Wikipedia
        
        Args:
            description: Human-readable description of the job
            years_back: How many years back to go (default: 20)
            shard_size: Number of movies per JSONL shard file (default: 100)
            start_immediately: Whether to start processing immediately
            
        Returns:
            job_id: Unique identifier for tracking this job
        """
        # Calculate year range
        current_year = datetime.now().year
        start_year = current_year - years_back
        end_year = current_year - 1  # Don't include current year (incomplete)
        
        # Create job parameters
        parameters = {
            'task_type': 'movies_by_years',
            'years_back': years_back,
            'start_year': start_year,
            'end_year': end_year,
            'shard_size': shard_size,
            'total_years': end_year - start_year + 1
        }
        
        # Create job in database
        job_id = create_wiki_job('movies_by_years', description, parameters)
        
        logger.info(f"[Job {job_id}] Created movie collection job: {start_year}-{end_year} ({parameters['total_years']} years)")
        
        if start_immediately:
            self.start_job_processing(job_id)
        
        return job_id
    
    def start_job_processing(self, job_id: str) -> bool:
        """
        Start processing a queued job in a background thread
        
        Returns:
            bool: True if job was started, False if already running or failed to start
        """
        if job_id in self.running_jobs:
            logger.warning(f"[Job {job_id}] Already running")
            return False
        
        job_data = get_job_status(job_id)
        if not job_data:
            logger.error(f"[Job {job_id}] Job not found")
            return False
        
        if job_data['status'] not in ['queued', 'paused']:
            logger.warning(f"[Job {job_id}] Job status is {job_data['status']}, cannot start")
            return False
        
        # Start processing in background thread
        thread = threading.Thread(
            target=self._run_movie_collection_job,
            args=(job_id,),
            daemon=True,
            name=f"WikiJob-{job_id}"
        )
        
        self.running_jobs[job_id] = thread
        thread.start()
        
        logger.info(f"[Job {job_id}] Started processing in background thread")
        return True
    
    def _run_movie_collection_job(self, job_id: str):
        """
        Main job processing function (runs in background thread)
        This is where the long-running work happens
        """
        try:
            logger.info(f"[Job {job_id}] Starting movie collection job")
            update_job_status(job_id, 'running')
            
            # Get job parameters
            job_data = get_job_status(job_id)
            if not job_data:
                raise Exception("Job not found")
            
            params = job_data['parameters']
            start_year = params['start_year']
            end_year = params['end_year']
            shard_size = params['shard_size']
            
            # Phase 1: Discover all movie URLs by crawling category pages
            logger.info(f"[Job {job_id}] Phase 1: Discovering movies from {start_year} to {end_year}")
            movies_by_year = discover_movies_by_years(job_id, start_year, end_year)
            
            total_movies = sum(len(urls) for urls in movies_by_year.values())
            logger.info(f"[Job {job_id}] Discovery complete: {total_movies} movies found")
            
            if total_movies == 0:
                update_job_status(job_id, 'completed', items_total=0)
                logger.info(f"[Job {job_id}] No movies found, job completed")
                return
            
            # Phase 2: Scrape individual movie pages
            logger.info(f"[Job {job_id}] Phase 2: Scraping {total_movies} movie pages")
            
            output_dir = Path(job_data['data_folder'])
            scraper = MoviePageScraper(job_id, output_dir)
            
            results = scraper.scrape_movie_batch(movies_by_year, shard_size)
            
            # Job completed successfully
            update_job_status(
                job_id, 'completed',
                items_total=results['total_movies'],
                items_processed=results['processed'],
                items_failed=results['failed']
            )
            
            logger.info(f"[Job {job_id}] Job completed successfully!")
            logger.info(f"[Job {job_id}] Final stats: {results['processed']} processed, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"[Job {job_id}] Job failed with error: {e}")
            update_job_status(job_id, 'failed', last_error=str(e))
        
        finally:
            # Clean up
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a running job (not fully implemented - would need job coordination)"""
        if job_id not in self.running_jobs:
            return False
        
        update_job_status(job_id, 'paused')
        logger.info(f"[Job {job_id}] Job paused (note: current operations will complete)")
        return True
    
    def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress of a job"""
        return get_job_status(job_id)
    
    def list_all_jobs(self) -> list:
        """List all jobs with their current status"""
        from app.wiki.database import list_wiki_jobs
        return list_wiki_jobs()
    
    def get_job_results(self, job_id: str, limit: int = 100) -> list:
        """Get results from a completed job"""
        from app.wiki.database import get_job_results
        return get_job_results(job_id, limit)

# Global orchestrator instance
orchestrator = WikiMovieTaskOrchestrator()