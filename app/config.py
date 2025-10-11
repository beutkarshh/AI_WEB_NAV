import os
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS","true").lower()=="true"  # Default to headless
CONCURRENCY = int(os.getenv("CONCURRENCY",2))
PAGE_BUDGET = int(os.getenv("PAGE_BUDGET",1))
