def infer_brand(title_norm:str)->str|None:
    brands=["samsung","redmi","apple","vivo","oppo","oneplus","realme","motorola","hp","lenovo","asus","dell"]
    for b in brands:
        if title_norm.startswith(b+" ") or (" "+b+" ") in (" "+title_norm+" "):
            return b
    return None
