from playwright.sync_api import sync_playwright
from app.config import HEADLESS

def _try_click_consent(page):
    # Try a few common consent selectors; ignore errors
    for sel in ["#sp-cc-accept", "input[name='accept']",
                "button[name='accept']", "input#accept-choices"]:
        try:
            if page.locator(sel).first.is_visible():
                page.locator(sel).first.click(timeout=1000)
                return True
        except Exception:
            pass
    return False

def _bot_blocked(page) -> bool:
    try:
        txt = (page.content() or "")[:20000].lower()
        return ("automated access" in txt or "enter the characters" in txt or "sorry" in txt and "robot" in txt)
    except Exception:
        return False

def _scrape_single_page(page, site, page_num=1):
    """Scrape a single page and return page data"""
    try:
        site_name = site.get("name", "unknown")
        
        # Navigate to the appropriate page
        if page_num > 1 and "pagination_url" in site:
            # Use pagination URL for subsequent pages
            query = site.get("query", "")
            url = site["pagination_url"].format(query=query, page=page_num)
            print(f"[{site_name}] Loading page {page_num}: {url[:80]}...")
            page.goto(url, timeout=45000)
        elif page_num == 1:
            # First page uses search_url
            page.goto(site["search_url"], timeout=45000)
        else:
            # No pagination support for this site
            return None

        # Accept consent (mainly for first page)
        if page_num == 1:
            _try_click_consent(page)

        # Wait for content and scroll to trigger lazy loading
        page.wait_for_selector(site["wait_selectors"][0], timeout=45000)
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(1500)

        # Optional second scroll if few elements
        card_count = page.locator(site["card"]).count()
        if card_count < 5:
            page.evaluate("window.scrollBy(0, 1800)")
            page.wait_for_timeout(700)

        if _bot_blocked(page):
            print(f"[{site_name}] ⚠️  Bot detection on page {page_num}")
        
        return (site, page)
        
    except Exception as e:
        print(f"[{site_name}] ❌ Error on page {page_num}: {e}")
        return None

def run_sites(plan: dict):
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=HEADLESS,
        args=['--no-blink-features=AutomationControlled']
    )
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    )
    
    all_pages = []
    mode = plan.get("mode", "quick")
    max_pages = plan.get("max_pages", 1)
    
    for site in plan["sites"]:
        site_name = site["name"]
        pages_to_scrape = min(max_pages, site.get("max_pages", 1)) if mode == "deep" else 1
        
        print(f"\n[{site_name}] 🚀 Starting {mode} mode scraping ({pages_to_scrape} pages)")
        
        # Create a new page for this site
        p = ctx.new_page()
        
        # Hide webdriver properties
        p.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            window.chrome = {
                runtime: {},
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        # Scrape multiple pages for this site
        for page_num in range(1, pages_to_scrape + 1):
            result = _scrape_single_page(p, site, page_num)
            if result:
                all_pages.append(result)
                
                # Save screenshot for debugging (first page only)
                if page_num == 1:
                    try:
                        p.screenshot(path="data/artifacts/page_screenshot.png")
                        print("[debug] Screenshot saved to data/artifacts/page_screenshot.png")
                    except Exception:
                        pass
                
                card_count = p.locator(site["card"]).count()
                print(f"[{site_name}] ✅ Page {page_num}: Found {card_count} items")
                
                # Add delay between pages to avoid rate limiting
                if page_num < pages_to_scrape:
                    p.wait_for_timeout(2000)
            else:
                print(f"[{site_name}] ⏹️  Stopping at page {page_num} due to error")
                break

    return pw, browser, ctx, all_pages
