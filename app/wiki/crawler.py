"""
Wikipedia Category Crawler
Finds all movies by year using Category:<year>_films pages
"""

import requests
from selectolax.parser import HTMLParser
import time
import re
from typing import List, Set, Tuple, Dict, Any
from urllib.parse import urljoin, unquote
import logging
from datetime import datetime

from app.wiki.database import update_job_status

# Wikipedia base URLs
WIKIPEDIA_BASE = "https://en.wikipedia.org"
CATEGORY_URL_TEMPLATE = "https://en.wikipedia.org/wiki/Category:{year}_films"

# Request configuration
REQUEST_DELAY = 1.0  # Polite delay between requests
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

logger = logging.getLogger(__name__)

class WikipediaCategoryCrawler:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Web-Navigator/1.0 (Educational Research; https://github.com/beutkarshh/AI_WEB_NAV)'
        })
        
    def get_movies_for_year(self, year: int) -> List[str]:
        """
        Get all movie URLs for a specific year
        Returns list of Wikipedia URLs for movies in that year
        """
        movie_urls = set()
        page_num = 1
        
        logger.info(f"[Job {self.job_id}] Starting to crawl movies for year {year}")
        update_job_status(self.job_id, 'running', current_year=year, current_page=1)
        
        while True:
            category_url = self._build_category_url(year, page_num)
            logger.info(f"[Job {self.job_id}] Fetching page {page_num} for year {year}: {category_url}")
            
            try:
                # Fetch the category page
                response = self._make_request(category_url)
                if not response:
                    logger.error(f"[Job {self.job_id}] Failed to fetch {category_url}")
                    break
                    
                # Parse the HTML
                parser = HTMLParser(response.text)
                
                # Extract movie links from this page
                page_movies = self._extract_movie_links(parser)
                if not page_movies:
                    logger.info(f"[Job {self.job_id}] No movies found on page {page_num}, stopping")
                    break
                    
                movie_urls.update(page_movies)
                logger.info(f"[Job {self.job_id}] Found {len(page_movies)} movies on page {page_num} (total: {len(movie_urls)})")
                
                # Check if there's a next page
                has_next = self._has_next_page(parser)
                if not has_next:
                    logger.info(f"[Job {self.job_id}] No more pages for year {year}")
                    break
                    
                page_num += 1
                update_job_status(self.job_id, 'running', current_page=page_num)
                
                # Polite delay
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"[Job {self.job_id}] Error processing year {year}, page {page_num}: {e}")
                break
        
        movies_list = list(movie_urls)
        logger.info(f"[Job {self.job_id}] Completed year {year}: found {len(movies_list)} unique movies")
        return movies_list
    
    def get_all_movies_by_years(self, start_year: int, end_year: int) -> Dict[int, List[str]]:
        """
        Get all movies for a range of years
        Returns dict: {year: [movie_urls]}
        """
        all_movies = {}
        total_movies = 0
        
        for year in range(start_year, end_year + 1):
            try:
                movies = self.get_movies_for_year(year)
                all_movies[year] = movies
                total_movies += len(movies)
                
                # Update total count as we discover more movies
                update_job_status(self.job_id, 'running', items_total=total_movies)
                
                logger.info(f"[Job {self.job_id}] Year {year}: {len(movies)} movies (running total: {total_movies})")
                
            except Exception as e:
                logger.error(f"[Job {self.job_id}] Failed to process year {year}: {e}")
                all_movies[year] = []
        
        logger.info(f"[Job {self.job_id}] Discovery complete: {total_movies} movies across {len(all_movies)} years")
        return all_movies
    
    def _build_category_url(self, year: int, page_num: int = 1) -> str:
        """Build URL for a specific year's category page"""
        base_url = CATEGORY_URL_TEMPLATE.format(year=year)
        
        if page_num > 1:
            # Wikipedia uses continuation tokens for pagination, but we'll try this approach first
            return f"{base_url}?pagefrom={page_num}"
        return base_url
    
    def _make_request(self, url: str) -> requests.Response:
        """Make a request with retries and error handling"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"[Job {self.job_id}] Request attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        return None
    
    def _extract_movie_links(self, parser: HTMLParser) -> Set[str]:
        """Extract movie article links from a category page"""
        movie_urls = set()
        
        # Look for the main content area with category members
        content_div = parser.css_first('#mw-pages, .mw-category-group')
        if not content_div:
            # Try alternative selectors
            content_div = parser.css_first('#mw-content-text')
        
        if content_div:
            # Find all links that look like movie articles
            links = content_div.css('a[href^="/wiki/"]')
            
            for link in links:
                href = link.attrs.get('href')
                if href and self._is_movie_link(href, link.text()):
                    full_url = urljoin(WIKIPEDIA_BASE, href)
                    movie_urls.add(full_url)
        
        return movie_urls
    
    def _is_movie_link(self, href: str, link_text: str) -> bool:
        """
        Determine if a link is likely a movie article
        Filter out non-movie pages like redirects, categories, etc.
        """
        # Decode URL
        href = unquote(href)
        
        # Skip these types of pages
        skip_patterns = [
            'Category:', 'File:', 'Template:', 'Help:', 'User:', 'Talk:',
            'Wikipedia:', 'Special:', 'Portal:', 'Draft:', 'MediaWiki:',
            'Module:', 'TimedText:', 'Gadget:'
        ]
        
        for pattern in skip_patterns:
            if pattern in href:
                return False
        
        # Skip disambiguation pages and lists
        skip_terms = ['disambiguation', 'list of', 'filmography', 'discography']
        href_lower = href.lower()
        text_lower = (link_text or '').lower()
        
        for term in skip_terms:
            if term in href_lower or term in text_lower:
                return False
        
        # Must be in main namespace (starts with /wiki/ followed by article title)
        if not re.match(r'^/wiki/[^:]+$', href):
            return False
            
        return True
    
    def _has_next_page(self, parser: HTMLParser) -> bool:
        """Check if there's a next page in the category"""
        # Look for "next page" or "next 200" links
        next_links = parser.css('a')
        
        for link in next_links:
            link_text = (link.text() or '').lower()
            if any(phrase in link_text for phrase in ['next page', 'next 200', 'next']):
                href = link.attrs.get('href', '')
                if 'pagefrom=' in href or 'cmcontinue=' in href:
                    return True
        
        return False

def discover_movies_by_years(job_id: str, start_year: int, end_year: int) -> Dict[int, List[str]]:
    """
    Main function to discover all movies for a range of years
    """
    crawler = WikipediaCategoryCrawler(job_id)
    return crawler.get_all_movies_by_years(start_year, end_year)