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

## 2026-04-01 - Day 3: Capability Alignment Scoring Engine

### Completed
- `backend/capabilities/seed_capabilities.py` - seeds 3 capabilities: Remote Sensing (22 kw), 3D Point Clouds (21 kw), Edge Computing (23 kw)
- `backend/capabilities/prompts.py` - ALIGNMENT_SYSTEM + ALIGNMENT_USER templates; structured JSON response format
- `backend/capabilities/aligner.py` - two-pass scoring: keyword_score() (sqrt-normalized, whole-word regex) gates Claude API calls at threshold 0.15; semantic_score() calls claude-sonnet-4-6 with max_tokens=256; run_alignment() processes all solicitations
- `backend/routers/capabilities.py` - GET/POST /capabilities, POST /align/run (background), GET /align/status, GET /solicitations/{id}/alignment
- `backend/main.py` - capabilities router registered

### Performance
- 20 solicitations x 3 capabilities = 60 scores
- Only 5 Claude API calls triggered (keyword filter blocked 55/60)
- Zero errors

### Sample output
- ID 18 (SWaP Radar Warning Receiver): Remote Sensing score 0.200, Claude rationale: "RWR payloads involve radar signal detection/processing, not remote sensing data acquisition or imagery analysis"
- ID 3 (NAVWAR Post-Quantum Encryption): Edge Computing score 0.300 (keyword hit: embedded/advanced computing)

### Notes
- Keyword threshold 0.15 works well for this dataset - aggressive enough to block irrelevant topics, permissive enough for weak-signal matches
- `run_alignment()` is idempotent via `upsert_score` - safe to re-run after scraping new solicitations

### Verification
- `python -m backend.capabilities.seed_capabilities` -> "3 new capabilities seeded"
- `POST /align/run` -> background task, returns immediately
- `GET /align/status` -> `{"running": false, "last_stats": {"api_calls_made": 5, ...}}`
- `GET /solicitations/18/alignment` -> 3 scores with Claude rationale for Remote Sensing

---

## 2026-04-01 - Day 4: RAG Draft Generation Pipeline

### Completed
- `backend/rag/context_builder.py` - assembles context from solicitation + alignment scores + capability descriptions; formats as structured text block for prompt injection; truncates descriptions at 6000 chars
- `backend/rag/prompts.py` - DRAFT_SYSTEM, TECHNICAL_VOLUME_PROMPT (6 sections), COMMERCIALIZATION_PROMPT (6 sections); SECTION_PROMPTS dict for dispatch
- `backend/rag/generator.py` - `generate_draft(project_id, section_type)`: loads project -> solicitation -> builds context -> renders prompt -> calls claude-sonnet-4-6 (max_tokens=4096) -> persists to drafts table
- `backend/routers/projects.py` - POST /projects, GET /projects/{id}, POST /projects/{id}/generate, GET /projects/{id}/drafts
- `backend/main.py` - projects router registered
- 2 test projects created and drafts generated

### Sample output quality
- Project 1 (Cognitive Mapping, DTRA254-002, 0.850 3D Point Clouds): 17,302 char technical volume
  - Correctly referenced SLAM, g2o, loop-closure, LiDAR, GPS-denied environments
  - Technical approach grounded in actual problem domain
- Project 2 (Shop Floor Human Detection, AF254-D0823, 0.850 3D Point Clouds): 16,824 char technical volume

### Verification
- `POST /projects` body `{"solicitation_id": 81, "title": "..."}` -> 201, returns project + alignment scores
- `POST /projects/1/generate` body `{"section_type": "technical_volume"}` -> draft with 16-17k chars
- `GET /projects/1/drafts` -> `[{"id": 1, "section_type": "technical_volume", "content": "..."}]`

---

## 2026-04-01 - Day 5: React Frontend MVP + Sprint Complete

### Completed
- `frontend/src/api/client.js` - Axios instance; all API calls centralized (getSolicitations, getAlignment, createProject, generateDraft, getDrafts, triggerScrape, getScrapeStatus)
- `frontend/src/components/NavBar.jsx` - top nav with active-route highlighting
- `frontend/src/views/SolicitationList.jsx` - paginated table (25/page), top alignment score badge per row (green/yellow/gray), "Scrape New" button with polling
- `frontend/src/views/SolicitationDetail.jsx` - solicitation full text, 3 capability score cards with color-coded bars and Claude rationale, "Create Project" button navigates to DraftEditor
- `frontend/src/views/DraftEditor.jsx` - section type dropdown (Technical Volume / Commercialization Plan), Generate button, draft history sidebar, copy-to-clipboard, alignment summary strip
- `frontend/src/App.jsx` - React Router v6, 3 routes: /, /solicitations/:id, /projects/:id
- TailwindCSS v4 via @tailwindcss/vite - all styling in-component, no config file needed
- `npm run build` - clean production build (282 kB JS, 18 kB CSS, 0 errors)

### End-to-End Verification
- Backend: 3 endpoints confirmed (solicitations list, alignment scores, drafts)
- Frontend build: 79 modules, no errors or warnings
- Full flow: list -> detail -> create project -> generate draft -> copy

### Sprint Summary (Days 1-5)
- Day 1: Scaffold, FastAPI, SQLite schema (5 tables), CRUD layer
- Day 2: SBIR.gov scraper (httpx+BS4), 98 solicitations in DB, solicitations REST API
- Day 3: Capability alignment engine, 2-pass scoring, 3 capabilities, Claude API integration
- Day 4: RAG draft generator, context builder, Technical Volume + Commercialization Plan prompts, 16-17k char drafts
- Day 5: React/Vite/TailwindCSS frontend, 3 views, full end-to-end demo

---
