# browser/context/page factory, UA/viewport jitter, trace control
from playwright.async_api import async_playwright
from app.config import settings

async def launch_browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=settings.BROWSER_HEADLESS)
    ctx = await browser.new_context(user_agent="Mozilla/5.0 WebNavigator")
    page = await ctx.new_page()
    return pw, browser, ctx, page
