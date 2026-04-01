# HANDOFF

**Last updated:** 2026-04-01 (Day 3 complete)

---

## Current State

Days 1-3 complete. The backend scrapes, stores, and scores solicitations.
- 20 solicitations in DB (from 2-page test scrape)
- 3 capabilities seeded with keyword lists
- 60 alignment scores stored (5 Claude API calls, keyword filter blocked the rest)
- Frontend is still a stub

---

## What Was Built (Days 1-3)

- Full backend scaffold: FastAPI, SQLite schema (5 tables), CRUD layer
- SBIR.gov scraper: httpx + BeautifulSoup, two-phase pipeline
- Capability alignment: two-pass scoring (keyword gate + Claude API), 3 capabilities seeded
- REST API: solicitations, capabilities, alignment, scrape trigger

---

## Start Day 4

### Goal
Generate Technical Volume and Commercialization Plan draft sections for a project via Claude API RAG pipeline.

### Files to create
- `backend/rag/context_builder.py`
- `backend/rag/prompts.py`
- `backend/rag/generator.py`
- `backend/routers/projects.py`
- Register `projects` router in `backend/main.py`

### RAG context assembly
`context_builder.py` should pull:
1. Full solicitation text (title + description + topic_number + agency + deadline)
2. All capability scores for the solicitation (score + rationale for each)
3. Capability descriptions and keywords for top-scoring capabilities

### Prompt templates
- `TECHNICAL_VOLUME_PROMPT` - generates Background, Innovation, Technical Approach, Team stubs, Timeline
- `COMMERCIALIZATION_PROMPT` - generates Phase II commercial plan

### Generator
- `generate_draft(project_id, section_type)` -> pulls project -> solicitation -> scores -> builds context -> calls Claude -> persists to `drafts`
- Model: `claude-sonnet-4-6`, `max_tokens=4096`
- Section types: `"technical_volume"`, `"commercialization_plan"`

### Routes
- `POST /projects` body: `{"solicitation_id": int, "title": str}`
- `GET /projects/{id}`
- `POST /projects/{id}/generate` body: `{"section_type": "technical_volume"}`
- `GET /projects/{id}/drafts`

---

## How to Run

```bash
# Backend (from project root)
source backend/.venv/bin/activate
uvicorn backend.main:app --reload

# Scrape more data (more topics = better alignment diversity)
python backend/scraper/run_scrape.py --max-pages 10 --max-detail 100

# Re-run alignment after new scrapes
python -c "from backend.capabilities.aligner import run_alignment; run_alignment()"
```

---

## Schema Reference (do not change without logging)

```
solicitations(id, agency, title, topic_number, description, deadline, url UNIQUE, raw_html, scraped_at)
capabilities(id, name UNIQUE, description, keywords_json)
projects(id, solicitation_id FK, title, status, created_at)
drafts(id, project_id FK, section_type, content, model_version, generated_at)
solicitation_capability_scores(solicitation_id FK, capability_id FK, score, rationale, scored_at) PK(sol_id, cap_id)
```

## API Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /solicitations | List all solicitations (paginated, agency filter) |
| GET | /solicitations/{id} | Single solicitation |
| POST | /solicitations/scrape | Trigger background scrape |
| GET | /solicitations/scrape/status | Scrape job status |
| GET | /solicitations/{id}/alignment | Alignment scores for a solicitation |
| GET | /capabilities | List capabilities |
| POST | /capabilities | Add new capability |
| POST | /align/run | Trigger background alignment pass |
| GET | /align/status | Alignment job status |
