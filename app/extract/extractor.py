from pathlib import Path
from urllib.parse import urljoin

def extract_items(pages):
    results = []
    for site, page in pages:
        # Debug what's actually on the page
        debug_info = page.evaluate("""
() => {
  const allElements = document.querySelectorAll("*");
  const dataAsinElements = document.querySelectorAll("[data-asin]");
  const sResultItems = document.querySelectorAll(".s-result-item");
  const priceElements = document.querySelectorAll("[class*='price']");
  const titleElements = document.querySelectorAll("h2, h3, h4");
  
  return {
    totalElements: allElements.length,
    dataAsinCount: dataAsinElements.length,
    sResultItemCount: sResultItems.length,
    priceElementCount: priceElements.length,
    titleElementCount: titleElements.length,
    pageTitle: document.title,
    hasSearchResults: !!document.querySelector("#search"),
    hasMainSlot: !!document.querySelector(".s-main-slot")
  };
}
        """)
        print(f"[debug] Page analysis: {debug_info}")
        
        # use evaluate for speed, try multiple selectors
        data = page.evaluate("""
() => {
  const res = [];
  // Try different possible selectors
  const selectors = [
    "[data-asin]:not([data-asin=''])",
    ".s-result-item",
    "[data-component-type='s-search-result']",
    ".sg-col .s-result-item"
  ];
  
  let cards = [];
  for (const selector of selectors) {
    cards = Array.from(document.querySelectorAll(selector));
    if (cards.length > 0) break;
  }
  
  for (const c of cards) {
    const t = c.querySelector("h2 a span") || c.querySelector("h2 span") || c.querySelector("h2");
    const a = c.querySelector("h2 a") || c.querySelector("a[href*='/dp/']");
    const p = c.querySelector(".a-price .a-offscreen") || c.querySelector(".a-price-whole") || c.querySelector("[class*='price']");
    const r = c.querySelector(".a-icon-alt") || c.querySelector("[class*='star']");
    
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
        """)

        base = page.url
        fixed = []
        for d in data[: site.get("max_cards", 24)]:
            d["url"] = urljoin(base, d.get("url",""))
            d["site"] = site["name"]
            fixed.append(d)

        if not fixed:
            # dump the whole main slot for quick inspection
            try:
                slot_html = page.locator(".s-main-slot").first.inner_html(timeout=1000)
                Path("data/artifacts/slot_dump.html").write_text(slot_html, encoding="utf-8")
                print("[debug] wrote data/artifacts/slot_dump.html")
            except Exception:
                pass

        print(f"[{site['name']}] cards={len(data)} kept={len(fixed)}")
        results.extend(fixed)
    return results
