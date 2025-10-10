import re
def parse_inr(s:str)->int:
    if not s: return 0
    digits = re.sub(r"[^\d]","",s)
    return int(digits) if digits else 0
