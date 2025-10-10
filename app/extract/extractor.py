from pathlib import Path
from urllib.parse import urljoin

def extract_items(pages):
    results = []
    for site, page in pages:
        site_name = site.get("name", "unknown")
        
        # Debug what's actually on the page
        debug_info = page.evaluate("""
() => {
  const allElements = document.querySelectorAll("*");
  const dataAsinElements = document.querySelectorAll("[data-asin]");
  const dataIdElements = document.querySelectorAll("[data-id]");
  const sResultItems = document.querySelectorAll(".s-result-item");
  const priceElements = document.querySelectorAll("[class*='price']");
  const titleElements = document.querySelectorAll("h2, h3, h4");
  
  return {
    totalElements: allElements.length,
    dataAsinCount: dataAsinElements.length,
    dataIdCount: dataIdElements.length,
    sResultItemCount: sResultItems.length,
    priceElementCount: priceElements.length,
    titleElementCount: titleElements.length,
    pageTitle: document.title,
    hasSearchResults: !!document.querySelector("#search"),
    hasMainSlot: !!document.querySelector(".s-main-slot")
  };
}
        """)
        print(f"[debug] Page analysis for {site_name}: {debug_info}")
        
        # Use site-specific selectors from configuration
        card_selector = site.get("card", "[data-asin]:not([data-asin=''])")
        title_selector = site.get("sel_title", "h2 a span")
        link_selector = site.get("sel_link", "h2 a")
        price_selector = site.get("sel_price", ".a-price .a-offscreen")
        price_alt_selector = site.get("sel_price_alt", ".a-price-whole")
        rating_selector = site.get("sel_rating", ".a-icon-alt")
        
        # use evaluate for speed with site-specific selectors
        selectors = {
            "card": card_selector,
            "title": title_selector,
            "link": link_selector,
            "price": price_selector,
            "priceAlt": price_alt_selector,
            "rating": rating_selector
        }
        
        data = page.evaluate("""
(selectors) => {
  const res = [];
  const cards = Array.from(document.querySelectorAll(selectors.card));
  
  for (const c of cards) {
    // Try multiple title selectors
    const titleSelectors = selectors.title.split(', ');
    let t = null;
    for (const sel of titleSelectors) {
      t = c.querySelector(sel.trim());
      if (t) break;
    }
    
    // Try multiple link selectors
    const linkSelectors = selectors.link.split(', ');
    let a = null;
    for (const sel of linkSelectors) {
      a = c.querySelector(sel.trim());
      if (a) break;
    }
    
    // Try multiple price selectors
    const priceSelectors = [selectors.price, selectors.priceAlt].filter(Boolean);
    let p = null;
    for (const sel of priceSelectors) {
      p = c.querySelector(sel);
      if (p) break;
    }
    
    // Try rating selector
    const r = c.querySelector(selectors.rating);
    
    if (t || p) {
      const obj = {
        title: t ? t.textContent.trim() : "",
        url: a ? a.href : "",
        price_txt: p ? (p.textContent || "").trim() : "",
        rating_txt: r ? (r.textContent || "").trim() : ""
      };
      res.push(obj);
    }
  }
  return res;
}
        """, selectors)

        base = page.url
        fixed = []
        for d in data[: site.get("max_cards", 24)]:
            d["url"] = urljoin(base, d.get("url",""))
            d["site"] = site["name"]
            fixed.append(d)

        if not fixed:
            # dump page content for quick inspection - try different selectors based on site
            try:
                if site_name == "amazon":
                    slot_html = page.locator(".s-main-slot").first.inner_html(timeout=1000)
                elif site_name == "flipkart":
                    slot_html = page.locator("._1YokD2").first.inner_html(timeout=1000)
                else:
                    slot_html = page.content()
                
                Path(f"data/artifacts/{site_name}_dump.html").write_text(slot_html, encoding="utf-8")
                print(f"[debug] wrote data/artifacts/{site_name}_dump.html")
            except Exception as e:
                print(f"[debug] Could not dump {site_name} content: {e}")

        print(f"[{site['name']}] cards={len(data)} kept={len(fixed)}")
        results.extend(fixed)
    return results
