# ProposalPilot AI

RAG-based proposal automation engine for SBIR/STTR funding cycles. Scrapes
agency solicitations, scores them against user-defined technical capabilities,
and generates draft Technical Volumes and Commercialization Plans via the
Claude API.

## Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn, SQLite
- **Scraper**: Playwright (fallback: httpx + BeautifulSoup)
- **LLM**: Claude API (Anthropic SDK)
- **Frontend**: React, Vite, TailwindCSS

## Local Setup

### Prerequisites

- Python 3.12+
- Node 20+ (install via `fnm` or `nvm`)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp ../.env.example ../.env
# Edit .env and set ANTHROPIC_API_KEY

uvicorn backend.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

### Seed capabilities and run scraper (Day 2+)

```bash
python -m backend.capabilities.seed_capabilities
python backend/scraper/run_scrape.py --max-pages 2
```

## Database

SQLite at `proposalpilot.db` (auto-created on first backend start).

Tables: `solicitations`, `capabilities`, `projects`, `drafts`, `solicitation_capability_scores`

## Project Structure

```
backend/
  main.py            FastAPI app entry point
  config.py          Env/config loader
  database.py        SQLite connection + schema init
  models/schema.sql  DDL for all tables
  db/crud.py         Data access layer
  scraper/           Playwright scraper for SBIR.gov
  capabilities/      Capability seeding and alignment scoring
  rag/               Context builder and Claude API draft generator
  routers/           FastAPI route handlers
frontend/
  src/
    api/client.js    Axios API client
    views/           SolicitationList, SolicitationDetail, DraftEditor
    components/      NavBar
    App.jsx          React Router wiring
```
