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

def run_sites(plan:dict):
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
    pages=[]
    for site in plan["sites"]:
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
        
        p.goto(site["search_url"], timeout=45000)

        # accept consent if present
        _try_click_consent(p)

        # wait for main slot (container), then light scroll to trigger lazy load
        p.wait_for_selector(site["wait_selectors"][0], timeout=45000)
        p.wait_for_timeout(2000)  # Wait longer before scrolling
        p.evaluate("window.scrollBy(0, 1200)")
        p.wait_for_timeout(1500)  # Wait longer after scrolling

        # optional second scroll if few elements
        if p.locator(site["card"]).count() < 5:
            p.evaluate("window.scrollBy(0, 1800)")
            p.wait_for_timeout(700)

        if _bot_blocked(p):
            print("[amazon] Warning: bot/CAPTCHA page detected")
        
        # Save screenshot for debugging
        try:
            p.screenshot(path="data/artifacts/page_screenshot.png")
            print("[debug] Screenshot saved to data/artifacts/page_screenshot.png")
        except Exception:
            pass

        pages.append((site, p))
    return pw, browser, ctx, pages
