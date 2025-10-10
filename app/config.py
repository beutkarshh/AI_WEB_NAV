import os
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS","false").lower()=="true"
CONCURRENCY = int(os.getenv("CONCURRENCY",2))
PAGE_BUDGET = int(os.getenv("PAGE_BUDGET",1))
