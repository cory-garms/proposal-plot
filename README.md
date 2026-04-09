# ProposalPilot AI

RAG-based proposal automation engine for SBIR/STTR/BAA funding cycles. Scrapes agency solicitations from SBIR.gov, Grants.gov, and SAM.gov; scores them against user-defined technical capability profiles; and generates draft Technical Volumes and Commercialization Plans via configurable LLM providers.

## Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn, SQLite (WAL mode)
- **Scraper**: httpx + BeautifulSoup (SBIR.gov, Grants.gov, SAM.gov)
- **LLM**: Pluggable — Anthropic, OpenAI, Gemini, Ollama, or any OpenAI-compat endpoint
- **Frontend**: React 19, Vite, TailwindCSS v4
- **Auth**: JWT (HS256), bcrypt passwords, role-based (admin / user)
- **Scheduler**: APScheduler nightly alignment

## Deployment

### Production (GitHub Pages + Render)

See [HANDOFF.md](HANDOFF.md) for step-by-step deploy instructions.

- Frontend → GitHub Pages via GitHub Actions (`.github/workflows/deploy-frontend.yml`)
- Backend + DB → Render with persistent disk (`render.yaml`)

### Local Development

**Prerequisites:** Python 3.12+, Node 20+

```bash
cd proposal-pilot

# Backend
python -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# Set ANTHROPIC_API_KEY (or configure another LLM provider — see .env.example)

uvicorn backend.main:app --reload
# API: http://localhost:8000  |  Docs: http://localhost:8000/docs

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
# UI: http://localhost:5173
```

**First-time user setup:**
```bash
python -m backend.scraper.seed_users
# Creates cgarms (admin) + rpanfili, dstelter, rtaylor (beta users)
```

**Dev reset (wipe non-admin users):**
```bash
python -m backend.scraper.reset_beta_users
```

### Docker (local network)

```bash
cp .env.example .env  # edit JWT_SECRET and LLM config
docker compose up --build
# UI: http://<host-ip>:3000
```

## LLM Provider Configuration

Set in `.env` — swap without changing any code:

```bash
# Anthropic (default)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LLM_PROVIDER=openai_compat
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...

# Local (Ollama)
LLM_PROVIDER=openai_compat
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=   # blank
```

Also supports: Gemini, Kimi K2, GLM, LM Studio, vLLM, HuggingFace TGI.

## Features

- **Multi-source scraping**: SBIR.gov, Grants.gov, SAM.gov, DOD CSV import
- **Two-pass alignment**: keyword pre-filter gates LLM semantic scoring; content-hash dedup skips unchanged solicitations
- **Capability profiles**: per-user profiles; shared company profile (Spectral Sciences); auto-alignment on save
- **Capability generation**: paste ORCID, Google Scholar, or ResearchGate URL; upload PDF/DOCX CV; LLM extracts structured capability areas
- **Dashboard**: personalized per logged-in user; lifecycle buckets (TPOC window, open, closing, newly released, recently closed)
- **Draft generation**: Technical Volume + Commercialization Plan with RAG context; revision history + diff view
- **Role system**: admin (scraping, all profiles) vs user (own profile + shared read-only)
- **Nightly scheduler**: APScheduler runs alignment at 02:00 server time

## Project Structure

```
backend/
  main.py                    FastAPI app, lifespan, CORS
  config.py                  All env vars
  database.py                SQLite + additive migrations
  models/schema.sql          Table definitions
  db/crud.py                 Data access layer
  llm/                       LLM provider abstraction (Protocol + providers)
  routers/                   auth, capabilities, dashboard, solicitations,
                             keywords, projects, generate_capabilities
  capabilities/
    aligner.py               Two-pass keyword+LLM scoring, content-hash dedup
    prompts.py               Alignment prompt templates
  rag/
    extractor.py             ORCID, Google Scholar, ResearchGate, PDF, DOCX
    capability_generator.py  LLM → structured capability list
    generator.py             Draft generation
    context_builder.py       RAG context assembly
  scraper/
    seed_users.py            Bootstrap admin + beta accounts
    reset_beta_users.py      Dev reset script
  scheduler.py               APScheduler nightly job

frontend/
  src/
    api/client.js            Axios + JWT interceptors
    views/                   Dashboard, SolicitationList, SolicitationDetail,
                             Capabilities, GenerateCapabilities, Keywords,
                             Admin, DraftEditor, Login, ChangePassword
    components/NavBar.jsx
    App.jsx                  Router + RequireAuth guard

.github/workflows/
  deploy-frontend.yml        GitHub Actions → GitHub Pages

render.yaml                  Render Blueprint (backend + persistent disk)
docker-compose.yml           Local network Docker deployment
```

## Database

SQLite at `proposalpilot.db` (local) or `/data/proposalpilot.db` (Render disk).

Tables: `solicitations`, `users`, `profiles`, `capabilities`, `projects`, `drafts`, `solicitation_capability_scores`, `search_keywords`, `agency_release_schedule`, `sota_cache`
