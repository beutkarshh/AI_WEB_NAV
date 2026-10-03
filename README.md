# AI Web Nav

**An LLM-driven shopping agent that turns a plain-English request into a ranked, cross-site product comparison.**

🏆 **1st Runner-Up — ByteXL HackXLerate Hackathon**

Type `"running shoes under 4k"` and AI Web Nav works out what you mean, decides which stores are worth searching, drives a real browser through Amazon, Flipkart and Myntra, and returns one cleaned, de-duplicated, budget-filtered list.

---

## How it works

```
"nike shoes under 4k"
        │
        ▼
┌──────────────────┐   Local LLM (Ollama · qwen2.5:7b) → strict JSON:
│ 1. Intent parse  │   { category, brands, features, max_price }
└────────┬─────────┘   falls back to rule-based parsing if the LLM fails
         ▼
┌──────────────────┐   LLM picks the stores that fit the category
│ 2. Site select   │   (e.g. fashion → adds Myntra; electronics → Amazon + Flipkart)
└────────┬─────────┘
         ▼
┌──────────────────┐   Playwright drives a real browser per site,
│ 3. Browse        │   with per-site search profiles, consent-popup
└────────┬─────────┘   handling and bot-block detection
         ▼
┌──────────────────┐   In-page DOM queries with site-specific selectors
│ 4. Extract       │   (title, price, rating, link)
└────────┬─────────┘
         ▼
┌──────────────────┐   INR price + rating parsing, title normalisation,
│ 5. Normalise     │   brand inference, budget filter, de-duplication
└────────┬─────────┘
         ▼
┌──────────────────┐   Ranked by rating → price, stored in SQLite,
│ 6. Rank & store  │   returned via CLI table or REST API
└──────────────────┘
```

**Design choices worth noting**
- **Local LLM, not a hosted API** — no per-query cost and no user data leaving the machine; every LLM step has a deterministic fallback so a bad model response never kills a search.
- **LLM output is constrained to JSON** and defensively parsed (extracts the first `{…}` block, defaults missing fields).
- **Two modes** — `quick` (first page, top 5 per site, ~15s) and `deep` (multiple pages, all qualifying results).

## Round 2: long-running Wikipedia crawler

The hackathon's surprise round asked for a resumable, long-running data-collection task. `app/wiki/` implements it:

- Crawls Wikipedia's *"YYYY films"* categories (with pagination) to discover film pages over a configurable year range
- Scrapes each page's infobox into normalised fields, writing **sharded JSONL** output
- Job lifecycle tracked in SQLite — create, start, pause, poll progress — exposed as a REST API under `/wiki/jobs`

## Tech stack

`Python` · `Playwright` · `Selectolax` · `Ollama (qwen2.5:7b)` · `FastAPI` · `SQLite / SQLAlchemy` · `Pydantic`

## Run it locally

**Prerequisites:** Python 3.10+, and [Ollama](https://ollama.com) running locally (optional — the rule-based fallback works without it).

```bash
pip install -r requirements.txt
playwright install chromium
ollama pull qwen2.5:7b            # optional, enables LLM intent parsing + site selection

# CLI
python -m app.main "smartphones under 20000" --mode quick

# REST API  →  http://localhost:8000/docs
uvicorn app.api.server:app --reload
```

| Endpoint | Purpose |
|---|---|
| `POST /api/search` | Natural-language product search |
| `POST /api/compare` | Cross-site comparison |
| `GET /api/providers` | Supported stores |
| `POST /wiki/jobs` · `GET /wiki/jobs/{id}` | Start / track a Wikipedia crawl job |

> The auth endpoints are a demo stub for the hackathon frontend (any credentials are accepted) — not real authentication.

## Project layout

```
app/
├── nlu/        LLM client, intent parsing, site selection, query optimisation
├── plan/       per-site search plans + site profiles
├── browse/     Playwright context + site executor
├── extract/    HTML → raw product records
├── normalize/  price, rating, title and brand normalisation
├── output/     CLI table rendering
├── wiki/       Round 2 crawler, scraper, job orchestrator, API
├── api/        FastAPI server
└── utils/      SQLite schema, repositories, hashing
```

## Limitations & next steps

- Selectors are tied to current store markup and will need maintenance as sites change.
- Ranking is a simple rating → price sort; fuzzy cross-site grouping of the *same* product (e.g. with RapidFuzz) is the obvious next step.
- No automated test suite yet.

## Team

Built by **Utkarsh Waghmare** and **Aayush Angal** at HackXLerate.

MIT licensed.
