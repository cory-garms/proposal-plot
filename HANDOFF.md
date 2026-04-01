# HANDOFF

**Last updated:** 2026-04-01 (Day 1 complete)

---

## Current State

Day 1 scaffold is complete. The backend starts and initializes the database.
The frontend is scaffolded but empty (no views yet).

---

## What Was Built

- Full backend scaffold: FastAPI app, SQLite schema (5 tables), CRUD layer
- Frontend stub: React + Vite + TailwindCSS v4
- `backend/db/crud.py` is the authoritative data access layer - all future code routes through here

---

## Start Day 2

### Goal
Playwright scraper populates `solicitations` table; REST endpoints expose data.

### Files to create
- `backend/scraper/sbir_scraper.py`
- `backend/scraper/parser.py`
- `backend/scraper/run_scrape.py`
- `backend/routers/solicitations.py`
- Register `solicitations` router in `backend/main.py`

### Known risks
- SBIR.gov may require JS rendering or rate-limit aggressively
- If Playwright is blocked, fall back to `httpx` + `BeautifulSoup` and log the pivot

### How to run the backend
```bash
# From project root (proposal_pilot/)
source backend/.venv/bin/activate
uvicorn backend.main:app --reload
```

### Node path note
Node 20 is installed via `fnm`. To use npm/vite, run:
```bash
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
```

---

## Schema Reference (load-bearing - do not change without logging)

```
solicitations(id, agency, title, topic_number, description, deadline, url UNIQUE, raw_html, scraped_at)
capabilities(id, name UNIQUE, description, keywords_json)
projects(id, solicitation_id FK, title, status, created_at)
drafts(id, project_id FK, section_type, content, model_version, generated_at)
solicitation_capability_scores(solicitation_id FK, capability_id FK, score, rationale, scored_at) PK(sol_id, cap_id)
```
