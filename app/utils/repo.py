from sqlalchemy import text
from .db import SessionLocal

def create_run(run_id: str, query: str, sites_total:int):
    with SessionLocal() as s:
        s.execute(text("""INSERT INTO runs (id,query,started_at,sites_total)
                          VALUES (:id,:q,datetime('now'),:st)"""),
                  {"id":run_id,"q":query,"st":sites_total})
        s.commit()

def upsert_site(name:str)->int:
    with SessionLocal() as s:
        r=s.execute(text("SELECT id FROM sites WHERE name=:n"),{"n":name}).fetchone()
        if r: return r[0]
        s.execute(text("INSERT INTO sites(name) VALUES(:n)"),{"n":name}); s.commit()
        return s.execute(text("SELECT id FROM sites WHERE name=:n"),{"n":name}).fetchone()[0]

def insert_item(run_id, site_id, title, title_norm, brand, price_inr, rating, url, item_hash, source="live"):
    with SessionLocal() as s:
        s.execute(text("""INSERT OR IGNORE INTO items 
          (run_id,site_id,title,title_norm,brand,price_inr,rating,url,source,item_hash)
          VALUES (:r,:s,:t,:tn,:b,:p,:ra,:u,:src,:h)"""),
          {"r":run_id,"s":site_id,"t":title,"tn":title_norm,"b":brand,
           "p":price_inr,"ra":rating,"u":url,"src":source,"h":item_hash})
        s.commit()
