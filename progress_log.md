# Progress Log

---

## 2026-04-01 - Day 1: Project Scaffold

### Completed
- `git init`, `.gitignore`, `.env.example`, `README.md`
- Backend directory structure: `backend/{models,db,scraper,capabilities,rag,routers}`
- `backend/config.py` - dotenv loader for ANTHROPIC_API_KEY, DB_PATH, host/port
- `backend/database.py` - SQLite connection with WAL mode, foreign keys, row_factory; `init_db()` runs schema on startup
- `backend/models/schema.sql` - 5 tables: `solicitations`, `capabilities`, `projects`, `drafts`, `solicitation_capability_scores` with indexes
- `backend/main.py` - FastAPI app with lifespan-based `init_db()`, CORS for localhost:5173, `/health` endpoint
- `backend/db/crud.py` - full CRUD stub: upsert_solicitation, get_all_solicitations, get_solicitation_by_id, insert_capability, upsert_score, get_scores_for_solicitation, insert_project, get_project_by_id, insert_draft, get_drafts_for_project
- `backend/requirements.txt` - pinned: fastapi, uvicorn, anthropic, playwright, python-dotenv, httpx, beautifulsoup4
- Frontend scaffolded with `npm create vite -- --template react`, TailwindCSS v4 installed via `@tailwindcss/vite` plugin
- `frontend/.env` with `VITE_API_BASE_URL`

### Notes
- Node.js was not present on the system; installed via `fnm` with Node 20. Added to PATH via `$HOME/.fnm`.
- Tailwind v4 uses `@tailwindcss/vite` plugin, not `tailwind.config.js` — no separate config file needed.
- Backend import path uses `backend.` prefix (e.g., `uvicorn backend.main:app`) from the project root.

### Verification
- `curl http://localhost:8000/health` returns `{"status":"ok"}`
- `sqlite3 proposalpilot.db ".tables"` lists all 5 tables

---

## 2026-04-01 - Day 2: SBIR.gov Scraper + Solicitations API

### Completed
- `backend/scraper/parser.py` - HTML parsers for SBIR.gov listing (`/topics?status=1&page=N`) and detail (`/topics/{id}`) pages; extracts title, agency, topic_number, open/close dates, description, tags
- `backend/scraper/sbir_scraper.py` - async httpx scraper with two-phase pipeline: listing pages (10/page) + optional detail page enrichment; polite 0.75s delay between requests
- `backend/scraper/run_scrape.py` - CLI: `--max-pages N`, `--no-enrich`, `--max-detail N`; persists via crud.upsert_solicitation
- `backend/routers/solicitations.py` - `GET /solicitations`, `GET /solicitations/{id}`, `POST /scrape` (background task), `GET /solicitations/scrape/status`
- `backend/main.py` - solicitations router registered

### Pivot Notes
- **Playwright not needed.** SBIR.gov renders server-side. `httpx` + `BeautifulSoup` works cleanly. Playwright retained in requirements for future agency portal work.
- SBIR.gov listing at `/topics?status=1&page=N` returns 10 topics/page. Pagination works with `?page=N`.
- Detail pages (`/topics/{id}`) provide: topic_number, solicitation_number, full multi-paragraph description.
- Duplicate topic_numbers across different URLs are legitimate (SBIR reuses codes across cycles). Dedup is by URL (UNIQUE constraint).

### Verification
- `python backend/scraper/run_scrape.py --max-pages 2 --max-detail 10` -> "Persisted 20 solicitations (0 errors)"
- `GET /solicitations?limit=3` returns full JSON with descriptions (200+ word bodies)
- `GET /solicitations/1` returns single record with topic_number, agency, full description

---
