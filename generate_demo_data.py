"""
Quick Movie Data Generator for Demo
Creates sample movie data for evaluators to see
"""

import requests
from selectolax.parser import HTMLParser
import json
import time
from pathlib import Path
from datetime import datetime

def scrape_popular_movies():
    """Scrape a few popular movies quickly for demo"""
    
    # Sample of popular recent movies from Wikipedia
    movie_urls = [
        "https://en.wikipedia.org/wiki/Avatar:_The_Way_of_Water",
        "https://en.wikipedia.org/wiki/Top_Gun:_Maverick", 
        "https://en.wikipedia.org/wiki/Black_Panther:_Wakanda_Forever",
        "https://en.wikipedia.org/wiki/Doctor_Strange_in_the_Multiverse_of_Madness",
        "https://en.wikipedia.org/wiki/The_Batman_(film)",
        "https://en.wikipedia.org/wiki/Spider-Man:_No_Way_Home",
        "https://en.wikipedia.org/wiki/Dune_(2021_film)",
        "https://en.wikipedia.org/wiki/No_Time_to_Die",
    ]
    
    results = []
    output_dir = Path("data/demo_movies")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎬 Scraping popular movies for evaluator demo...")
    
    for i, url in enumerate(movie_urls, 1):
        try:
            print(f"[{i}/{len(movie_urls)}] Scraping: {url.split('/')[-1].replace('_', ' ')}")
            
            # Make request with proper headers
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'AI-Web-Navigator-Demo/1.0 (Educational Research)'
            })
            response.raise_for_status()
            
            # Parse HTML
            parser = HTMLParser(response.text)
            
            # Extract title
            title_elem = parser.css_first('h1.firstHeading, h1#firstHeading')
            title = title_elem.text().strip() if title_elem else "Unknown Title"
            
            # Extract infobox data
            infobox_data = {}
            infobox = parser.css_first('table.infobox')
            
            if infobox:
                rows = infobox.css('tr')
                for row in rows:
                    label_cell = row.css_first('th')
                    value_cell = row.css_first('td')
                    
                    if label_cell and value_cell:
                        label = label_cell.text().strip().lower()
                        value = value_cell.text().strip()
                        
                        # Clean up value
                        value = ' '.join(value.split())  # Remove extra whitespace
                        if len(value) < 300 and value:  # Reasonable length
                            # Normalize field names
                            if 'directed' in label:
                                infobox_data['director'] = value
                            elif 'produced' in label:
                                infobox_data['producer'] = value
                            elif 'starring' in label or 'cast' in label:
                                infobox_data['starring'] = value
                            elif 'release' in label:
                                infobox_data['release_date'] = value
                            elif 'running' in label or 'runtime' in label:
                                infobox_data['running_time'] = value
                            elif 'budget' in label:
                                infobox_data['budget'] = value
                            elif 'box office' in label or 'gross' in label:
                                infobox_data['box_office'] = value
                            elif 'country' in label:
                                infobox_data['country'] = value
                            elif 'language' in label:
                                infobox_data['language'] = value
                            else:
                                infobox_data[label.replace(' ', '_')] = value
            
            # Create movie record
            movie_data = {
                "title": title,
                "url": url,
                "scraped_at": datetime.now().isoformat(),
                "year": 2022,  # Most are recent
                **infobox_data
            }
            
            results.append(movie_data)
            print(f"   ✅ Successfully scraped: {title}")
            
            # Polite delay
            time.sleep(1.5)
            
        except Exception as e:
            print(f"   ❌ Failed to scrape {url}: {e}")
            continue
    
    # Save results
    output_file = output_dir / "sample_movies.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Also save as JSONL (one per line)
    jsonl_file = output_dir / "sample_movies.jsonl" 
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for movie in results:
            json.dump(movie, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"\n✅ Demo complete! Scraped {len(results)} movies")
    print(f"📂 Files saved:")
    print(f"   • {output_file}")
    print(f"   • {jsonl_file}")
    
    return results

if __name__ == "__main__":
    movies = scrape_popular_movies()
    
    print(f"\n🎬 Sample Movie Data for Evaluators:")
    print("=" * 50)
    
    for movie in movies[:3]:  # Show first 3 movies
        print(f"\n📽️  {movie['title']}")
        if 'director' in movie:
            print(f"   🎬 Director: {movie['director']}")
        if 'starring' in movie:
            starring = movie['starring'][:100] + "..." if len(movie['starring']) > 100 else movie['starring']
            print(f"   ⭐ Starring: {starring}")
        if 'box_office' in movie:
            print(f"   💰 Box Office: {movie['box_office']}")
        if 'budget' in movie:
            print(f"   💸 Budget: {movie['budget']}")
        print(f"   🔗 {movie['url']}")