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
