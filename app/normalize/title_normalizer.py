import re
def normalize_title(s:str)->str:
    s=(s or "").lower()
    s=re.sub(r"[^a-z0-9\s\-+]", "", s)
    return re.sub(r"\s+"," ", s).strip()
