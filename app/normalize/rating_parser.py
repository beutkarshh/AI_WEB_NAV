import re
def parse_rating(s:str)->float:
    if not s: return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*out of\s*5", s, re.I)
    return float(m.group(1)) if m else 0.0
