# HANDOFF

**Last updated:** 2026-04-09 (Sprint 9 deploy — Claude)

---

## Immediate Next Steps (Start Here)

Sprint 9: deploy live. GitHub Pages URL is `https://cory-garms.github.io/proposal-pilot/`.
`render.yaml` and all CORS references have been updated to `https://cory-garms.github.io`.

### Step 1 — GitHub Pages setup
1. Repo Settings → Pages → Source: **GitHub Actions**
2. Repo Settings → **Secrets** → New: `VITE_API_BASE_URL` = `https://proposalpilot-api.onrender.com` (confirm exact service name in Render after blueprint deploys)
3. Repo Settings → **Variables** → New: `VITE_BASE_PATH` = `/proposal-pilot/`
4. Push to `main` (already done) — workflow fires automatically, deploys to `https://cory-garms.github.io/proposal-pilot/`

### Step 2 — Render backend setup
1. Render dashboard → **New → Blueprint** → connect `cory-garms/proposal-pilot` repo → reads `render.yaml` automatically
2. Set your LLM API key in Render dashboard → Environment → `ANTHROPIC_API_KEY`
3. After first deploy, confirm the service URL and update `VITE_API_BASE_URL` secret in GitHub if it differs

### Step 3 — Upload the database (CONFIRMED: use existing local DB)
The Render disk starts empty. Upload `proposalpilot.db` from your local machine:
```bash
# Option A: Render CLI (install: npm i -g @render/cli or brew install render)
render ssh proposalpilot-api
# In a separate terminal:
scp proposalpilot.db <paste-ssh-target-from-render-cli-output>:/data/proposalpilot.db

# Option B: Render dashboard → Shell tab
# First, get the SSH address from Render dashboard → Service → Shell → "SSH" button
# Then from local WSL terminal:
scp /home/cgarms/Sandbox/proposal_pilot/proposal-pilot/proposalpilot.db \
    <render-ssh-user@render-ssh-host>:/data/proposalpilot.db
```
After upload, restart the service from the Render dashboard so FastAPI picks up the new DB.

### Step 4 — Verify
1. Open `https://cory-garms.github.io/proposal-pilot/` — should show Login page
2. Login as `cgarms@spectral.com` with your local password
3. Dashboard should show solicitations populated from the uploaded DB
4. Run a small alignment from Admin to confirm LLM calls work

---

## What Was Built This Session (Sprint 8)

### Bug Fixes
- **Capability delete** — was failing silently due to FK constraint on `solicitation_capability_scores`. Fixed: delete scores first, then capability.
- **Admin profile dropdown** — only showed admin's own + shared profiles. Fixed: `get_all_profiles(include_all=True)` for admin users.
- **Score button on shared profile** — 403 at backend. Fixed: button disabled when selected profile has `shared=1`.
- **Trailing "0" on profile heading** — `profile.shared` is SQLite integer `0`; React rendered it as text. Fixed: `!!profile.shared`.

### Capability Generator
- **Broader categories** — prompt now instructs LLM to use wide domain names and include both specific + parent terms in keywords. Fixes low match rate.
- **Google Scholar extractor** — `_extract_google_scholar()` in `extractor.py`: name, interests, publication list.
- **ResearchGate extractor** — `_extract_researchgate()`: scrapes HTML; graceful error when Cloudflare blocks.
- **Auto-routing** — `extract_from_url()` detects hostname and routes to specialized extractor.

### Dev Tooling
- `backend/scraper/reset_beta_users.py` — wipes all non-admin users/profiles/capabilities, recreates the three betas with `Welcome!2026`.

### Infrastructure
- **Content-hash deduplication** — `solicitations.content_hash` (SHA-256 title+description), `solicitation_capability_scores.scored_hash`. `get_scored_pairs()` now invalidates stale pairs on re-scrape. Eliminates redundant LLM calls when solicitation content hasn't changed.
- **CORS** — `CORS_ORIGINS` env var in `config.py`. Defaults to `*` locally; `render.yaml` sets it to `https://cgarms.github.io`.
- **GitHub Actions** — `.github/workflows/deploy-frontend.yml`. Triggers on `frontend/` changes to `main`. Uses `VITE_API_BASE_URL` secret + `VITE_BASE_PATH` variable.
- **SPA routing** — `frontend/public/404.html` + `index.html` inline redirect script. Handles direct-URL access on GitHub Pages without hash routing.
- **Render manifest** — `render.yaml`: web service + 1 GB persistent disk at `/data`. Starter plan ($7/mo) required for disk.

---

## Current State

### Database (local dev — `proposalpilot.db`)
| Table | Count |
|-------|-------|
| solicitations | 824 |
| scored pairs | 324 |
| capabilities | 39 |
| profiles | 5 |
| users | 4 |
| active keywords | 776 |

### Profiles
| ID | Name | Owner | Capabilities |
|----|------|-------|-------------|
| 1 | Cory Garms | cgarms (admin) | 11 |
| 2 | Spectral Sciences | shared (all users) | 10 |
| 3 | Panfili | rpanfili | 6 |
| 4 | David Stelter | dstelter | 6 |
| 5 | Ramona Taylor | rtaylor | 6 |

### Users
| Email | Role |
|-------|------|
| cgarms@spectral.com | admin |
| rpanfili@spectral.com | user |
| dstelter@spectral.com | user |
| rtaylor@spectral.com | user |

---

## How to Run (Local Dev)

```bash
cd proposal-pilot

# Backend
source backend/.ppEnv/bin/activate
uvicorn backend.main:app --reload

# Frontend (separate terminal)
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev

# Open http://localhost:5173
# Login: cgarms@spectral.com
```

### Useful dev commands
```bash
# Reset beta users to never-logged-in state
python -m backend.scraper.reset_beta_users

# Re-seed users if DB is fresh
python -m backend.scraper.seed_users

# Trigger scrape + full alignment
curl -X POST http://localhost:8000/solicitations/scrape/sam \
  -H 'Authorization: Bearer <token>' \
  -d '{"max_results": 100}'

curl -X POST 'http://localhost:8000/align/run?skip_scored=true' \
  -H 'Authorization: Bearer <token>'
```

---

## Architecture Overview

```
frontend/                    React + Vite + TailwindCSS v4
  src/
    views/                   Dashboard, SolicitationList, Capabilities,
                             Keywords, Admin, GenerateCapabilities,
                             ChangePassword, Login, DraftEditor
    components/NavBar.jsx
    api/client.js            Axios instance with JWT interceptors

backend/
  main.py                    FastAPI app, lifespan, CORS, router registration
  config.py                  All env vars (LLM, DB, auth, CORS, scheduler)
  database.py                SQLite connection, WAL mode, additive migrations
  scheduler.py               APScheduler nightly alignment
  llm/                       Provider abstraction (Anthropic, OpenAI-compat)
  routers/
    auth.py                  JWT login/register/me/password-change
    capabilities.py          Profiles, capabilities CRUD, alignment triggers
    dashboard.py             Per-user lifecycle buckets (TPOC, open, closing…)
    solicitations.py         List, detail, watch, scrape triggers
    keywords.py              Keyword CRUD
    generate_capabilities.py URL + file → LLM → capability suggestions
    projects.py              Draft generation
  db/crud.py                 All DB operations
  capabilities/
    aligner.py               Two-pass keyword+LLM scoring
    prompts.py               Alignment prompt templates
  rag/
    extractor.py             ORCID API, Google Scholar, ResearchGate, PDF, DOCX
    capability_generator.py  LLM → structured capability list
    generator.py             Draft generation
    context_builder.py       RAG context assembly
  scraper/
    seed_users.py            Create admin + beta accounts
    reset_beta_users.py      Dev reset — wipe non-admin users
```

---

## Known Issues / Deferred Work

### Sprint 9 backlog
- **Embedding-based pre-filter** — replace keyword threshold with cosine similarity on `text-embedding-3-small` vectors. Cuts LLM scoring calls ~60%. Defer until production traffic data shows whether content-hash fix is sufficient.
- **Render cold-start** — free Render tier spins down after 15 min idle (~30s cold start). Starter plan ($7/mo, already required for disk) stays warm.
- **`bcrypt<4.0.0` pin** — `passlib 1.7.4` breaks with `bcrypt>=4`. Pin is in `requirements.txt`. Don't upgrade bcrypt.
- **SAM CSV import** — `backend/scraper/sam_csv_parser.py` and `POST /solicitations/import/sam-csv` exist but are untested. May need validation before relying on it.
- **Capability auto-score on edit** — `PATCH /capabilities/{id}` now triggers background alignment (added this session). Not yet verified end-to-end.

### API auth table (updated)
Routes that require auth (`require_user` or stricter):

| Method | Path | Auth |
|--------|------|------|
| POST | /auth/password | require_user |
| POST | /profiles | require_user |
| POST | /capabilities | require_user (own profile) |
| PATCH | /capabilities/{id} | require_user (own profile) |
| DELETE | /capabilities/{id} | require_user (own profile) |
| POST | /align/run | require_own_profile_or_admin |
| POST | /solicitations/scrape* | require_admin |
| POST | /solicitations/import/sam-csv | require_admin |
| POST | /capabilities/generate/* | require_user |
| POST | /projects | require_user |
| POST | /projects/{id}/generate | require_user |
| PATCH | /projects/{id}/drafts/{id} | require_user |

---

## File Inventory (changed this sprint)

| File | Change |
|------|--------|
| `backend/database.py` | +2 migrations: `solicitations.content_hash`, `solicitation_capability_scores.scored_hash` |
| `backend/config.py` | +`CORS_ORIGINS` |
| `backend/main.py` | CORS reads from `CORS_ORIGINS` config |
| `backend/db/crud.py` | `_content_hash()`, `get_all_profiles(include_all)`, `delete_capability` cascades scores, `get_scored_pairs` hash-aware, `upsert_score` stores hash, `upsert_solicitation` stores hash |
| `backend/capabilities/aligner.py` | passes `content_hash` to `upsert_score` |
| `backend/rag/extractor.py` | Google Scholar + ResearchGate extractors; `extract_from_url` routes by hostname |
| `backend/rag/capability_generator.py` | Broader keyword/category prompt |
| `backend/routers/capabilities.py` | Admin sees all profiles; `edit_capability` triggers background alignment |
| `frontend/src/views/Capabilities.jsx` | Score button respects `shared`; `!!profile.shared` fix |
| `frontend/index.html` | Title fix; SPA redirect script |
| `frontend/public/404.html` | GitHub Pages 404 redirect |
| `frontend/vite.config.js` | `base` from `VITE_BASE_PATH` |
| `.env.example` | +`CORS_ORIGINS`, +`DB_PATH` production example |
| `.github/workflows/deploy-frontend.yml` | **new** — GitHub Actions deploy |
| `render.yaml` | **new** — Render Blueprint |
| `backend/scraper/reset_beta_users.py` | **new** — dev reset script |
