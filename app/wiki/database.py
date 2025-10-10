"""
Wikipedia Job Management Database Schema
Separate from e-commerce database for long-running tasks
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Wikipedia jobs database file
WIKI_DB_PATH = Path("data/wiki_jobs.db")
WIKI_DATA_DIR = Path("data/wiki_jobs")

def init_wiki_db():
    """Initialize Wikipedia jobs database with required tables"""
    WIKI_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    WIKI_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(WIKI_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wiki_jobs (
            job_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,  -- 'movies_by_years', 'categories', etc.
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',  -- queued, running, paused, completed, failed
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            
            -- Job parameters (JSON)
            parameters TEXT NOT NULL,  -- {"years_back": 20, "start_year": 2004, "end_year": 2024}
            
            -- Progress tracking
            items_total INTEGER DEFAULT 0,     -- Total movies to scrape
            items_processed INTEGER DEFAULT 0, -- Movies completed
            items_failed INTEGER DEFAULT 0,    -- Movies that failed
            
            -- Current state
            current_year INTEGER,              -- Which year we're currently processing
            current_page INTEGER DEFAULT 1,   -- Which page within that year
            
            -- Results info
            output_format TEXT DEFAULT 'jsonl', -- jsonl, json, csv
            data_folder TEXT,                   -- data/wiki_jobs/{job_id}/
            
            -- Error tracking
            last_error TEXT,
            error_count INTEGER DEFAULT 0,
            
            -- Performance metrics
            items_per_hour REAL DEFAULT 0.0,
            estimated_completion TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wiki_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT 'movie',
            year INTEGER,
            
            -- Scraped data as JSON
            raw_data TEXT,  -- Full infobox data as JSON
            
            -- Key extracted fields for quick queries
            director TEXT,
            producer TEXT,
            starring TEXT,
            release_date TEXT,
            running_time TEXT,
            country TEXT,
            language TEXT,
            budget TEXT,
            box_office TEXT,
            distributor TEXT,
            
            -- Metadata
            scraped_at TEXT NOT NULL,
            shard_file TEXT,  -- Which JSONL file contains this record
            
            FOREIGN KEY (job_id) REFERENCES wiki_jobs (job_id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wiki_job_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            category_url TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            movies_found INTEGER DEFAULT 0,
            movies_scraped INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, failed
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            
            FOREIGN KEY (job_id) REFERENCES wiki_jobs (job_id),
            UNIQUE(job_id, year, page_number)
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wiki_entities_job ON wiki_entities(job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wiki_entities_year ON wiki_entities(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wiki_progress_job ON wiki_job_progress(job_id)")
    
    conn.commit()
    conn.close()

def create_wiki_job(task_type: str, description: str, parameters: Dict[str, Any]) -> str:
    """Create a new Wikipedia scraping job"""
    import uuid
    
    job_id = f"wiki_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:8]}"
    data_folder = WIKI_DATA_DIR / job_id
    data_folder.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(WIKI_DB_PATH)
    conn.execute("""
        INSERT INTO wiki_jobs (
            job_id, task_type, description, status, created_at, 
            parameters, data_folder
        ) VALUES (?, ?, ?, 'queued', ?, ?, ?)
    """, (
        job_id, task_type, description, datetime.now().isoformat(), 
        json.dumps(parameters), str(data_folder)
    ))
    conn.commit()
    conn.close()
    
    return job_id

def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status and other fields"""
    conn = sqlite3.connect(WIKI_DB_PATH)
    
    updates = ["status = ?"]
    values = [status]
    
    if status == 'running' and 'started_at' not in kwargs:
        kwargs['started_at'] = datetime.now().isoformat()
    elif status in ('completed', 'failed') and 'completed_at' not in kwargs:
        kwargs['completed_at'] = datetime.now().isoformat()
    
    for key, value in kwargs.items():
        if key in ['items_total', 'items_processed', 'items_failed', 'current_year', 
                  'current_page', 'started_at', 'completed_at', 'last_error', 
                  'error_count', 'items_per_hour', 'estimated_completion']:
            updates.append(f"{key} = ?")
            values.append(value)
    
    values.append(job_id)
    
    conn.execute(f"UPDATE wiki_jobs SET {', '.join(updates)} WHERE job_id = ?", values)
    conn.commit()
    conn.close()

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get current job status and progress"""
    conn = sqlite3.connect(WIKI_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("SELECT * FROM wiki_jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        job_data = dict(row)
        job_data['parameters'] = json.loads(job_data['parameters'])
        
        # Calculate progress percentage
        if job_data['items_total'] > 0:
            job_data['progress_percent'] = (job_data['items_processed'] / job_data['items_total']) * 100
        else:
            job_data['progress_percent'] = 0.0
            
        return job_data
    return None

def list_wiki_jobs() -> List[Dict[str, Any]]:
    """List all Wikipedia jobs"""
    conn = sqlite3.connect(WIKI_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT job_id, task_type, description, status, created_at, 
               items_total, items_processed, items_failed,
               (CASE 
                   WHEN items_total > 0 THEN ROUND((items_processed * 100.0 / items_total), 2)
                   ELSE 0.0 
               END) as progress_percent
        FROM wiki_jobs 
        ORDER BY created_at DESC
    """)
    
    jobs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jobs

def add_wiki_entity(job_id: str, url: str, title: str, year: int, 
                   raw_data: Dict[str, Any], shard_file: str) -> int:
    """Add a scraped movie entity to the database"""
    conn = sqlite3.connect(WIKI_DB_PATH)
    
    # Extract key fields from raw_data for quick querying
    director = raw_data.get('director', '')
    producer = raw_data.get('producer', '')
    starring = raw_data.get('starring', '')
    release_date = raw_data.get('release_date', '')
    running_time = raw_data.get('running_time', '')
    country = raw_data.get('country', '')
    language = raw_data.get('language', '')
    budget = raw_data.get('budget', '')
    box_office = raw_data.get('box_office', '')
    distributor = raw_data.get('distributor', '')
    
    cursor = conn.execute("""
        INSERT INTO wiki_entities (
            job_id, url, title, year, raw_data, director, producer, starring,
            release_date, running_time, country, language, budget, box_office,
            distributor, scraped_at, shard_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id, url, title, year, json.dumps(raw_data), director, producer, 
        starring, release_date, running_time, country, language, budget,
        box_office, distributor, datetime.now().isoformat(), shard_file
    ))
    
    entity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return entity_id

def get_job_results(job_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Get results for a completed job"""
    conn = sqlite3.connect(WIKI_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute("""
        SELECT * FROM wiki_entities 
        WHERE job_id = ? 
        ORDER BY year DESC, title
        LIMIT ? OFFSET ?
    """, (job_id, limit, offset))
    
    results = []
    for row in cursor.fetchall():
        result = dict(row)
        result['raw_data'] = json.loads(result['raw_data'])
        results.append(result)
    
    conn.close()
    return results