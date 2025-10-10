import hashlib
def item_hash(site:str, title_norm:str, price_inr:int)->str:
    return hashlib.sha1(f"{site}|{title_norm}|{price_inr}".encode()).hexdigest()
