"""
Wikipedia Movie Page Scraper
Extracts movie information from individual Wikipedia movie pages
"""

import requests
from selectolax.parser import HTMLParser
import time
import json
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import logging
from datetime import datetime
from pathlib import Path

from app.wiki.database import add_wiki_entity, update_job_status

logger = logging.getLogger(__name__)

class MoviePageScraper:
    def __init__(self, job_id: str, output_dir: Path):
        self.job_id = job_id
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Web-Navigator/1.0 (Educational Research; https://github.com/beutkarshh/AI_WEB_NAV)'
        })
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def scrape_movie_batch(self, movies_by_year: Dict[int, List[str]], 
                          shard_size: int = 100) -> Dict[str, Any]:
        """
        Scrape a batch of movies organized by year
        Outputs to JSONL shards and database
        """
        total_movies = sum(len(urls) for urls in movies_by_year.values())
        processed = 0
        failed = 0
        
        logger.info(f"[Job {self.job_id}] Starting to scrape {total_movies} movies")
        update_job_status(self.job_id, 'running', items_total=total_movies)
        
        results = {
            'total_movies': total_movies,
            'processed': 0,
            'failed': 0,
            'years_processed': [],
            'shard_files': []
        }
        
        for year, movie_urls in movies_by_year.items():
            if not movie_urls:
                continue
                
            logger.info(f"[Job {self.job_id}] Processing {len(movie_urls)} movies for year {year}")
            update_job_status(self.job_id, 'running', current_year=year)
            
            # Create year directory
            year_dir = self.output_dir / str(year)
            year_dir.mkdir(exist_ok=True)
            
            # Process movies in shards
            shard_num = 0
            for i in range(0, len(movie_urls), shard_size):
                batch = movie_urls[i:i + shard_size]
                shard_num += 1
                
                shard_file = year_dir / f"part_{shard_num:03d}.jsonl"
                logger.info(f"[Job {self.job_id}] Processing shard {shard_num} for year {year}: {len(batch)} movies")
                
                batch_processed, batch_failed = self._process_movie_batch(
                    batch, year, shard_file
                )
                
                processed += batch_processed
                failed += batch_failed
                
                # Update progress
                update_job_status(
                    self.job_id, 'running', 
                    items_processed=processed, 
                    items_failed=failed
                )
                
                results['shard_files'].append(str(shard_file))
                
                # Calculate performance metrics
                self._update_performance_metrics(processed, total_movies)
                
                logger.info(f"[Job {self.job_id}] Shard {shard_num} complete: {batch_processed} processed, {batch_failed} failed")
            
            results['years_processed'].append(year)
            logger.info(f"[Job {self.job_id}] Year {year} complete: {len(movie_urls)} movies")
        
        results['processed'] = processed
        results['failed'] = failed
        
        logger.info(f"[Job {self.job_id}] Scraping complete: {processed} processed, {failed} failed")
        return results
    
    def _process_movie_batch(self, movie_urls: List[str], year: int, 
                           shard_file: Path) -> tuple[int, int]:
        """Process a batch of movies and write to JSONL file"""
        processed = 0
        failed = 0
        
        with open(shard_file, 'w', encoding='utf-8') as f:
            for i, url in enumerate(movie_urls):
                try:
                    movie_data = self._scrape_single_movie(url, year)
                    if movie_data:
                        # Write to JSONL file
                        json.dump(movie_data, f, ensure_ascii=False)
                        f.write('\n')
                        
                        # Add to database
                        add_wiki_entity(
                            self.job_id, url, movie_data['title'], year,
                            movie_data, str(shard_file)
                        )
                        
                        processed += 1
                        logger.debug(f"[Job {self.job_id}] Scraped: {movie_data['title']}")
                    else:
                        failed += 1
                        logger.warning(f"[Job {self.job_id}] Failed to scrape: {url}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"[Job {self.job_id}] Error scraping {url}: {e}")
                
                # Polite delay between requests
                if i < len(movie_urls) - 1:  # Don't delay after last item
                    time.sleep(1.0)
        
        return processed, failed
    
    def _scrape_single_movie(self, url: str, year: int) -> Optional[Dict[str, Any]]:
        """Scrape a single movie page and extract infobox data"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            parser = HTMLParser(response.text)
            
            # Extract title from page
            title = self._extract_title(parser)
            if not title:
                return None
            
            # Find and parse infobox
            infobox_data = self._extract_infobox(parser)
            
            # Build complete movie data
            movie_data = {
                'title': title,
                'url': url,
                'year': year,
                'scraped_at': datetime.now().isoformat(),
                **infobox_data
            }
            
            return movie_data
            
        except Exception as e:
            logger.error(f"[Job {self.job_id}] Error scraping {url}: {e}")
            return None
    
    def _extract_title(self, parser: HTMLParser) -> Optional[str]:
        """Extract movie title from the page"""
        # Try multiple selectors for the title
        title_selectors = [
            'h1.firstHeading',
            'h1#firstHeading', 
            '.mw-page-title-main',
            'h1'
        ]
        
        for selector in title_selectors:
            title_elem = parser.css_first(selector)
            if title_elem:
                title = title_elem.text(strip=True)
                if title:
                    return title
        
        return None
    
    def _extract_infobox(self, parser: HTMLParser) -> Dict[str, Any]:
        """Extract data from the movie infobox"""
        infobox_data = {}
        
        # Find infobox table
        infobox = parser.css_first('table.infobox')
        if not infobox:
            return infobox_data
        
        # Extract key-value pairs from infobox rows
        rows = infobox.css('tr')
        
        for row in rows:
            # Look for header/label cell
            label_cell = row.css_first('th, .infobox-label')
            value_cell = row.css_first('td, .infobox-data')
            
            if label_cell and value_cell:
                label = self._clean_text(label_cell.text())
                value = self._clean_text(value_cell.text())
                
                if label and value:
                    # Normalize common field names
                    normalized_label = self._normalize_field_name(label)
                    infobox_data[normalized_label] = value
        
        return infobox_data
    
    def _normalize_field_name(self, label: str) -> str:
        """Normalize infobox field names to standard keys"""
        label = label.lower().strip()
        
        # Common field mappings
        field_mappings = {
            'directed by': 'director',
            'director': 'director',
            'produced by': 'producer',
            'producer': 'producer',
            'starring': 'starring',
            'written by': 'writer',
            'screenplay by': 'screenplay',
            'story by': 'story',
            'music by': 'music',
            'cinematography': 'cinematography',
            'edited by': 'editor',
            'production company': 'production_company',
            'distributed by': 'distributor',
            'release date': 'release_date',
            'released': 'release_date',
            'running time': 'running_time',
            'runtime': 'running_time',
            'country': 'country',
            'language': 'language',
            'budget': 'budget',
            'box office': 'box_office',
            'gross': 'box_office',
        }
        
        return field_mappings.get(label, label.replace(' ', '_'))
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ''
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove reference markers like [1], [citation needed]
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[citation needed\]', '', text)
        text = re.sub(r'\[.*?\]', '', text)
        
        return text.strip()
    
    def _update_performance_metrics(self, processed: int, total: int):
        """Update job performance metrics"""
        if processed == 0:
            return
            
        # This is a simplified calculation - in a real system you'd track time
        # For now, just update the progress
        progress_percent = (processed / total) * 100 if total > 0 else 0
        
        # Estimate items per hour (placeholder calculation)
        items_per_hour = processed * 0.5  # Rough estimate
        
        update_job_status(
            self.job_id, 'running',
            items_per_hour=items_per_hour
        )