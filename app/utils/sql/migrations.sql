CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, query TEXT NOT NULL, started_at TEXT NOT NULL,
  finished_at TEXT, sites_ok INTEGER DEFAULT 0, sites_total INTEGER DEFAULT 0,
  items_seen INTEGER DEFAULT 0, items_kept INTEGER DEFAULT 0,
  matched_pairs INTEGER DEFAULT 0, duration_ms INTEGER, summary_json TEXT
);
CREATE TABLE IF NOT EXISTS sites (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, site_id INTEGER NOT NULL,
  title TEXT NOT NULL, title_norm TEXT NOT NULL, brand TEXT,
  price_inr INTEGER NOT NULL, rating REAL DEFAULT 0.0,
  url TEXT NOT NULL, source TEXT DEFAULT 'live',
  item_hash TEXT NOT NULL, UNIQUE(run_id, item_hash)
);
