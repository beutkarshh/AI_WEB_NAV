from typing import Dict, List, Any
import time

def _category_filter_js(category: str) -> str:
    if (category or "laptop").lower() != "laptop":
        return "t => true"
    return r"""t => /\b(laptop|notebook|macbook|chromebook)\b/i.test(t)"""

async def _grab_flipkart(page, cat_pred_js: str, no_filter: bool) -> List[Dict[str, Any]]:
    js = f"""
    (cards) => {{
        const keep = {("t => true" if no_filter else cat_pred_js)};
        const out = [];
        for (const c of cards.slice(0, 80)) {{
            const tEl = c.querySelector('div._4rR01T') || c.querySelector('a.s1Q9rs');
            const title = tEl ? tEl.innerText.trim() : null;
            if (!title || !keep(title)) continue;
            const priceEl = c.querySelector('div._30jeq3');
            const price = priceEl ? priceEl.textContent.trim() : null;
            const linkEl = c.querySelector('a._1fQZEK') || c.querySelector('a.s1Q9rs');
            const link = linkEl ? linkEl.href : null;
            const imgEl = c.querySelector('img._396cs4, img._2r_T1I');
            const img = imgEl ? imgEl.src : null;
            out.push({{ title, price, link, img }});
        }}
        return out;
    }}
    """
    return await page.eval_on_selector_all("[data-id]", js)

async def _grab_amazon(page, cat_pred_js: str, no_filter: bool) -> List[Dict[str, Any]]:
    js = f"""
    (cards) => {{
        const keep = {("t => true" if no_filter else cat_pred_js)};
        const out = [];
        for (const c of cards.slice(0, 80)) {{
            const textAll = (c.textContent || "").toLowerCase();
            if (textAll.includes("sponsored")) continue;
            const tnode = c.querySelector('h2 a span') || c.querySelector('h2 a');
            const title = tnode ? (tnode.textContent || '').trim() : null;
            if (!title || !keep(title)) continue;
            const price = c.querySelector('span.a-price span.a-offscreen')?.textContent?.trim() || null;
            const linkEl = c.querySelector('h2 a');
            const link = linkEl ? linkEl.href : null;
            const imgEl = c.querySelector('img.s-image');
            const img = imgEl ? imgEl.src : null;
            out.push({{ title, price, link, img }});
        }}
        return out;
    }}
    """
    sel = "div.s-main-slot [data-component-type='s-search-result']"
    return await page.eval_on_selector_all(sel, js)

async def search_site(page, site_profile: Dict[str, Any], query: str, category: str = "laptop") -> List[Dict[str, Any]]:
    url = site_profile["search_url"].format(q=query.replace(" ", "+"))
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector(site_profile["wait"], timeout=15000)

    # small scroll to trigger lazy load
    await page.evaluate("window.scrollBy(0, 1000)")
    await page.wait_for_timeout(400)

    cat_pred = _category_filter_js(category)

    # Count raw cards for debug
    if site_profile["name"] == "flipkart":
        raw_count = await page.eval_on_selector_all("[data-id]", "els => els.length")
        items = await _grab_flipkart(page, cat_pred, no_filter=False)
        if not items:
            # retry once without category filter
            items = await _grab_flipkart(page, cat_pred, no_filter=True)
    elif site_profile["name"] == "amazon":
        raw_count = await page.eval_on_selector_all("div.s-main-slot [data-component-type='s-search-result']", "els => els.length")
        items = await _grab_amazon(page, cat_pred, no_filter=False)
        if not items:
            items = await _grab_amazon(page, cat_pred, no_filter=True)
    else:
        raw_count = 0
        items = []

    # Save a quick screenshot into artifacts for debugging empty cases
    if not items:
        ts = int(time.time())
        try:
            await page.screenshot(path=f"data/artifacts/{site_profile['name']}-{ts}.png", full_page=True)
        except Exception:
            pass

    # Attach debug counts into items[0]._debug if needed (not used further)
    return items
