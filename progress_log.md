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

## 2026-04-02 - Day 6: Capability Expansion and Scraper Planning (Gemini)

### Completed
- Analyzed `ssi_sbir_history.csv` to extract 5 company-wide core competencies based on actual award history.
- `backend/capabilities/seed_capabilities.py` modified to support multi-profile seeding ("Cory Garms" and "Spectral Sciences").
- Profile ID 1 renamed to "Cory Garms"; Profile ID 2 created as "Spectral Sciences".
- Executed `seed_capabilities.py` to populate the production database with 10 total active capabilities across two profiles.
- Drafted `implementation_plan.md` for integrating Grants.gov (`/search2` API) and SAM.gov (Opportunities API) to capture BAAs and OTAs.

### Next Steps Handoff
- Execute the Grants.gov and SAM.gov scraper implementations based on user feedback to the open questions.

---

## 2026-04-08 - Sprint 7 (Claude)

### Day 1: Own-Profile Alignment
- `require_own_profile_or_admin` dependency in `auth.py`: admins can run for any/all profiles; non-admins must specify a `profile_id` they own
- `POST /align/run` changed from `require_admin` → `require_own_profile_or_admin`
- `Capabilities.jsx`: "Score My Profile" green button for non-admins; requires profile filter selection; polls `GET /align/status` and shows result inline

### Day 2: Scheduled Nightly Alignment
- `backend/scheduler.py`: APScheduler `BackgroundScheduler` with `CronTrigger`; default 02:00 server time
- Config vars: `SCHEDULER_ENABLED`, `SCHEDULER_HOUR`, `SCHEDULER_MINUTE` in `.env`
- Wired into FastAPI lifespan (`start_scheduler` / `stop_scheduler`)
- `GET /config` now includes `scheduler` block with enabled state and next run time
- `Admin.jsx`: `SchedulerCard` component shows schedule status and next run time
- `apscheduler==3.10.4` added to requirements

### Day 3: Capability Extraction Pipeline
- `backend/rag/extractor.py`: three extraction paths:
  - `extract_from_orcid(url_or_id)` — hits ORCID public API JSON, extracts name/bio/employment/publications; strips residual XML tags from titles
  - `extract_from_url(url)` — httpx + BeautifulSoup; auto-routes ORCID HTML URLs to API handler
  - `extract_from_pdf(bytes)` — pymupdf (fitz); handles most CVs cleanly
  - `extract_from_docx(bytes)` — python-docx; all truncated at 12k chars for LLM context
- `backend/rag/capability_generator.py`: LLM prompt returning JSON array of `{name, description, keywords}`; strips markdown fences; validates structure
- `backend/routers/generate_capabilities.py`: `POST /capabilities/generate/url`, `POST /capabilities/generate/file` (multipart); both require auth; 10 MB file limit
- `pymupdf>=1.24.0` added to requirements

**ORCID test (rpanfili — 0000-0002-1605-0331):**
- Extraction: clean, 20 publications, employment at Spectral Sciences confirmed
- Two research phases visible: atmospheric/IR modeling (2002–present, primary), atomic/laser physics (pre-2002, background)

### Day 4: Capability Generation UI
- `frontend/src/views/GenerateCapabilities.jsx`: three-step wizard (Input → Review & Edit → Done)
  - Step 1: URL/ORCID tab or file upload tab
  - Step 2: editable capability cards (name, description, keywords); per-capability include/exclude checkbox; profile selector
  - Step 3: success state with links to Capabilities page or generate more
- `Capabilities.jsx`: "Generate from Profile" purple button links to `/capabilities/generate`
- `App.jsx`: `/capabilities/generate` route added
- `client.js`: `generateCapabilitiesFromUrl`, `generateCapabilitiesFromFile`

### Day 5: Testing and Polish
- Verified ORCID extraction produces clean text after adding `_strip_xml_tags()` to handle `<emph>` in publication titles
- All new Python files pass `ast.parse()` syntax check
- `apscheduler` and `pymupdf` installed into `.ppEnv`

---

## 2026-04-08 - Sprint 6 (Claude)

### Day 3: LLM Abstraction Layer

**Goal:** decouple all LLM calls from the Anthropic SDK so any commercial or local model can be swapped in without code changes.

**New files:**
- `backend/llm/__init__.py` — package marker
- `backend/llm/base.py` — `LLMClient` Protocol: `complete(system, user, max_tokens) -> str` + `model` attribute
- `backend/llm/anthropic_provider.py` — wraps `anthropic` SDK; used when `LLM_PROVIDER=anthropic`
- `backend/llm/openai_compat_provider.py` — wraps `openai` SDK with configurable `base_url`; covers OpenAI, Gemini, Kimi K2, GLM, Ollama, LM Studio, vLLM, HuggingFace TGI
- `backend/llm/factory.py` — `get_llm_client()` cached singleton factory; `reset_llm_client()` for test teardown

**Modified:**
- `backend/config.py` — added `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`; kept `ANTHROPIC_API_KEY` for backward compat
- `backend/requirements.txt` — added `openai>=1.30.0`
- `backend/rag/generator.py` — removed direct `anthropic` import; now calls `get_llm_client().complete()`; `model_version` written to DB comes from `llm.model`
- `backend/capabilities/aligner.py` — removed `anthropic` import and `MODEL` constant; `semantic_score()` now typed to `LLMClient`; `run_alignment()` calls `get_llm_client()`
- `backend/main.py` — added `_validate_config()` startup check (warns on default JWT_SECRET, missing API keys, misconfigured provider); added `GET /config` endpoint (returns provider/model info to frontend, never secrets)

### Day 4: Docker Packaging

**Goal:** single `docker compose up --build` deploys the full stack on any machine; works on any host IP without rebuilding.

**Architecture:** browser → nginx (port 3000) → `/api/*` proxied to backend (internal port 8000) → SQLite volume

**New files:**
- `Dockerfile` — backend; python:3.12-slim; copies `backend/` only; DB mounted as volume
- `frontend/Dockerfile` — two-stage: Node 20 Alpine builds with `VITE_API_BASE_URL=/api`; nginx:alpine serves dist
- `frontend/nginx.conf` — proxies `/api/` → `http://backend:8000/`; SPA fallback; 300s timeout for long-running jobs
- `docker-compose.yml` — backend + frontend services; shared `internal` bridge network; DB volume mount; healthcheck on `/health`
- `.env.example` — documents all options for Anthropic, OpenAI, Gemini, Kimi K2, GLM, Ollama, LM Studio, vLLM
- `.dockerignore` — excludes .env, db files, venv, node_modules, dist from build context

**Key design decision:** frontend always built with `VITE_API_BASE_URL=/api` in Docker; nginx handles the host-to-backend translation. This means the image is host-IP-agnostic.

### Day 5: First-Run Onboarding

**New files:**
- `setup.sh` — local dev setup: creates .env, generates JWT_SECRET if default, creates venv, installs deps, inits DB, seeds capabilities if empty, installs frontend deps
- `BETA_SETUP.md` — step-by-step Docker deployment guide for non-technical beta users; covers LLM provider selection, network access, data persistence, troubleshooting

### Notes
- Days 1 and 2 (Admin UI + Profile/User Scoping) were already complete from Sprint 5 and required no changes.
- `openai` package is always installed regardless of provider; it's small and avoids conditional install complexity.
- Anthropic SDK is still installed even when using `openai_compat`; kept for future use and because it's already pinned.

---

## 2026-04-02 - Sprint 5 (Claude)

### Day 1: SOTA Caching + Draft Revision History UI
- Added `sota_cache(solicitation_id, query, papers_json, fetched_at)` table to schema + live DB
- `fetch_papers_cached()` in `sota.py`: 7-day TTL check before hitting arXiv; non-fatal on cache errors
- `context_builder.py` updated to use cached fetch — ~2s saved on repeated draft generation
- `GET /projects/{id}/drafts/{draft_id}/diff?against={other_id}`: unified diff via Python `difflib`
- `DraftEditor.jsx`: section type badge (Tech/Comm) + char count on each draft history entry
- Diff toggle button in content header — color-coded line view (green additions, red removals)

### Day 2: Keyword Management UI
- `backend/routers/keywords.py` (new): full CRUD router (`GET/POST/PATCH/DELETE /keywords`)
- `frontend/src/views/Keywords.jsx` (new): table with source badges, active toggle, delete, search + filter bar, inline add form; optimistic toggle
- `/keywords` route in App.jsx + NavBar link

### Day 3: SAM.gov Scraper
- `backend/scraper/sam_scraper.py` (new): queries `ptype=k` + `ptype=p` against 20 domain clusters
- Same keyword-cluster strategy as Grants.gov scraper
- TPOC extraction from `pointOfContact` array; agency normalization map
- Rate-limited: 6.5s/req without key, 0.7s/req with `SAM_API_KEY` env var
- `POST /solicitations/scrape/sam` + `GET /solicitations/scrape/sam/status` in solicitations router

### Day 4: Solicitation Detail Page Improvements
- `SolicitationDetail.jsx` rewritten: agency/branch chip (`DOD / Army`), vehicle type badge (color-coded), TPOC card, watch star (optimistic toggle), `navigate(-1)` back button

### Day 5: User Authentication (JWT)
- `users(id, email, hashed_password, created_at)` table; `profiles.user_id` nullable FK (existing data unaffected)
- `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart` added to requirements
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_HOURS` in config.py
- `backend/routers/auth.py` (new): `POST /auth/register`, `POST /auth/login` (OAuth2 form), `GET /auth/me`
- Protected: `POST /projects`, `POST /projects/{id}/generate`, `PATCH /projects/{id}/drafts/{id}` require Bearer token; read routes remain public
- `frontend/src/views/Login.jsx` (new): combined login/register page
- `client.js`: request interceptor attaches `Authorization: Bearer`; response interceptor redirects to `/login` on 401
- NavBar: "Sign out" button; login page hides NavBar via `useLocation`

### DB State at Sprint End
- 224 solicitations (173 SBIR, 1 STTR, 50 Grant), 100% scored
- 607 active keywords, 0 users (first login creates account at `/login`)
- `sota_cache` table present and empty (will populate on first draft generation)

---

---

## 2026-04-09 - Sprint 8 (Claude)

### Bug Fixes

**Capability delete broken (FK constraint)**
- `delete_capability()` in `crud.py` was failing silently due to FK violation: `solicitation_capability_scores` references `capability_id` with no CASCADE.
- Fix: delete matching rows from `solicitation_capability_scores` before deleting the capability.

**Admin profile dropdown missing non-admin users**
- `GET /profiles` called `get_all_profiles(user_id=user["id"])` for admins, returning only own + shared profiles.
- Fix: `get_all_profiles()` gains `include_all=True` param; admin path calls it with that flag, returning all profiles across all users.

**Non-admin "Score My Profile" button state**
- Score button was only gated on `profileFilter === 'all'`; if SSI (shared) was selected, the request would 403 at the backend.
- Fix: button also checks `!sel.shared`; disabled with correct tooltip when a shared profile is selected.

**Profile heading showed "PANFILIO" (trailing zero)**
- `profile.shared` is stored as `0`/`1` (SQLite integer). `{profile.shared && <span>...</span>}` in React renders `0` as literal text after the profile name.
- Fix: changed to `{!!profile.shared && ...}` to coerce to boolean.

### Capability Generator Improvements

**Broader capability categories**
- AI prompt updated in `capability_generator.py`: prefer broad domain names over project-specific titles; keywords now must include parent domain terms alongside specific ones (e.g., both "hyperspectral imaging" AND "remote sensing").
- Reduces over-specificity that was causing low keyword hit rates against solicitations.

**ResearchGate + Google Scholar support**
- `extractor.py`: dedicated `_extract_google_scholar()` and `_extract_researchgate()` functions added.
- Google Scholar: extracts name, research interests, publication list from HTML.
- ResearchGate: scrapes page HTML; returns helpful fallback message when Cloudflare blocks access.
- `extract_from_url()` now auto-routes based on hostname before falling back to generic scrape.

### Dev Tooling

**Beta user reset script**
- `backend/scraper/reset_beta_users.py`: deletes all non-admin users and their personal profiles/capabilities (cascades scores), then recreates rpanfili, dstelter, rtaylor with temp password `Welcome!2026`.
- Run: `python -m backend.scraper.reset_beta_users`

### Deployment Infrastructure (Sprint 8)

**Content-hash deduplication**
- `solicitations.content_hash` column: SHA-256 of `title + description`, computed on every `upsert_solicitation()`.
- `solicitation_capability_scores.scored_hash` column: stores the hash at scoring time.
- `get_scored_pairs()` now only skips a pair when `scored_hash == current content_hash` — changed/new content automatically triggers re-scoring on next alignment run.
- DB migrations added for both columns in `database.py`.

**CORS lockdown**
- `CORS_ORIGINS` env var added to `config.py`; defaults to `*` for local dev.
- `main.py` reads from config instead of hardcoded `*`.
- Set to `https://cgarms.github.io` in `render.yaml` for production.

**GitHub Actions CI/CD**
- `.github/workflows/deploy-frontend.yml`: triggers on push to `main` when `frontend/` changes; builds with `VITE_API_BASE_URL` and `VITE_BASE_PATH` from repo secrets/variables; deploys to GitHub Pages via `actions/deploy-pages`.

**GitHub Pages SPA routing**
- `frontend/public/404.html`: GitHub Pages 404 redirect trick — converts path to `?p=` query param.
- `frontend/index.html`: inline script restores the path via `history.replaceState` before React Router mounts.
- `frontend/vite.config.js`: `base` set from `VITE_BASE_PATH` env var (default `/`).

**Render deployment manifest**
- `render.yaml`: defines web service + 1 GB persistent disk mounted at `/data`; `DB_PATH=/data/proposalpilot.db`; `JWT_SECRET` auto-generated by Render; `ALLOW_REGISTRATION=false` for production; nightly scheduler enabled.

### DB State at Sprint End
| Table | Count |
|-------|-------|
| solicitations | 824 |
| scored pairs | 324 |
| capabilities | 39 (across 5 profiles) |
| profiles | 5 (Cory Garms, Spectral Sciences, Panfili, David Stelter, Ramona Taylor) |
| users | 4 (cgarms admin + 3 betas) |
| active keywords | 776 |

---

## 2026-04-09 - Sprint 9: Production Deploy (Claude)

### Completed

**Infrastructure fixes**
- Pinned Python to 3.12 via `.python-version` — Render was defaulting to 3.14, where `greenlet` (APScheduler dep) has no prebuilt wheel and fails to compile
- Fixed `$PORT` expansion: wrapped startCommand in `sh -c "uvicorn ... --port ${PORT:-10000}"` — Render's blueprint runner does not shell-expand bare `$PORT`
- Fixed lifespan blocking: moved `init_db()` into `asyncio.to_thread()` so uvicorn can serve `/health` while the DB initializes; added startup log lines
- Removed `playwright` from requirements (unused, was pulling ~300MB of chromium driver)
- Pinned `anthropic>=0.25.0,<0.28.0` to drop 13 transitive packages (HuggingFace tokenizers + CLI tools added in 0.28+); our `messages.create()` usage is API-stable since 0.17

**Frontend deploy**
- Fixed `npm ci` failure: GitHub Actions runner uses Node 20, local is Node 24 — native binary lock file entries diverged. Changed workflow to Node 24 + `npm install`
- Fixed React Router: `BrowserRouter` was missing `basename`; set to `import.meta.env.BASE_URL` (Vite's built-in, already set from `VITE_BASE_PATH`)
- Fixed all `window.location.href = '/login'` hardcodes: NavBar logout and `client.js` 401 interceptor now use `import.meta.env.BASE_URL + 'login'`

**URL corrections**
- All `cgarms.github.io` references updated to `cory-garms.github.io` (actual GitHub account username)

**DB upload**
- WAL checkpointed locally (`PRAGMA wal_checkpoint(FULL)`)
- Uploaded `proposalpilot.db` (8.5 MB) to Render persistent disk via SCP
- SSH key: `~/.ssh/id_rsa_personal` registered in Render Account Settings
- Render SSH target: `srv-d7buv6fkijhs73b1mkfg@ssh.oregon.render.com`

### Live URLs
| Service | URL |
|---------|-----|
| Frontend | `https://cory-garms.github.io/proposal-pilot/` |
| Backend | Render `proposalpilot-api`, Oregon, Starter plan |
| Repo | `https://github.com/cory-garms/proposal-pilot` |

### DB State at Sprint End (production = local upload)
| Table | Count |
|-------|-------|
| solicitations | 824 |
| scored pairs | 324 |
| capabilities | 39 |
| profiles | 5 |
| users | 4 |
| active keywords | 776 |

---

## 2026-04-10 - Sprint 10 Day 1: Beta Prep + Bug Fixes (Claude)

### DB Recovery
- Original `/data/proposalpilot.db` on Render disk became corrupted during failed SCP attempts (service was restarting mid-transfer)
- Recovery process: local `sqlite3 .dump | sqlite3` rebuild produces clean file; `DB_PATH` changed to `/data/proposalpilot2.db` in Render env vars
- Safe upload procedure going forward: always dump-and-rebuild locally, then SCP the clean file

### Deployment Fixes
- `anthropic==0.34.2` pin restored — version range `>=0.25,<0.28` caused Render build timeouts (PyPI resolution issue on their build environment)
- `init_db()` moved to `asyncio.create_task` so health check is never blocked by DB initialization (reverted after rollback issues; stable commit is `c1a546a`)
- Sign out button now uses `useNavigate('/login')` instead of `window.location.href` — React Router respects `basename` automatically

### Features
- **Generate Outline** — prompt rewritten to produce structured bullet outlines (writing guides) instead of full draft prose; `max_tokens` reduced 4096 → 1500; UI labels updated
- **Keywords tab** — hidden from non-admin users
- **Keyword cleanup** — 5 keywords with leading apostrophe fixed in DB: 3 deleted (dupes of clean versions), 2 updated

### Bug Fixes (found during Jim Grassi pre-beta session)
- **Capabilities profile dropdown** — now defaults to user's own profile on load instead of "All profiles"
- **Add capability form** — `profile_id` was hardcoded to `1` (Cory's profile); now initializes from active dropdown selection
- **Solicitation detail wrong profile** — `getAlignment` was falling back to `profileId=1` for all non-admin users; now fetches user's own profile dynamically
- **Dashboard empty for new users** — backend now falls back to SSI shared profile for sort/display when user has no personal scores; once they score their own capabilities, both appear

### Users (production DB as of session end)
| Email | Role |
|-------|------|
| cgarms@spectral.com | admin |
| rpanfili@spectral.com | user |
| dstelter@spectral.com | user |
| rtaylor@spectral.com | user |
| jgrassi@spectral.com | user (pre-beta tester) |

