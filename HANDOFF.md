# HANDOFF

**Last updated:** 2026-04-01 (Day 4 complete)

---

## Current State

Days 1-4 complete. Full backend pipeline is working end-to-end.
- 98 solicitations in DB, all scored
- 3 capabilities seeded
- 2 test projects created, 2 technical volume drafts generated (16-17k chars each)
- Frontend is still a stub — that's Day 5

---

## What Was Built (Days 1-4)

- Full backend scaffold: FastAPI, SQLite schema (5 tables), CRUD layer
- SBIR.gov scraper: httpx + BeautifulSoup, two-phase pipeline
- Capability alignment: two-pass scoring (keyword gate + Claude API)
- RAG draft generator: context builder + prompt templates + Claude claude-sonnet-4-6
- REST API: solicitations, capabilities, alignment, projects, drafts

---

## Start Day 5

### Goal
3-view React frontend that connects to all backend endpoints. Full local demo in browser.

### Files to create
- `frontend/src/api/client.js` - Axios instance, all API calls here
- `frontend/src/components/NavBar.jsx`
- `frontend/src/views/SolicitationList.jsx` - table + top alignment badge + "Scrape New" button
- `frontend/src/views/SolicitationDetail.jsx` - full text + color-coded score cards
- `frontend/src/views/DraftEditor.jsx` - section selector + Generate button + copy-to-clipboard
- `frontend/src/App.jsx` - React Router v6 routes

### Install needed
```bash
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm install react-router-dom axios
```

### Color coding for alignment scores
- >= 0.7 green
- 0.4-0.69 yellow
- < 0.4 red/gray

### Key solicitations to demo with
- ID 81: Cognitive Mapping for Counter-WMD (DTRA254-002) - score 0.850 3D Point Clouds
- ID 103: Shop Floor Human Detection (AF254-D0823) - score 0.850 3D Point Clouds
- ID 50: Real-Time Detection and Tracking - score 0.700 Edge Computing

---

## Full API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /solicitations?limit=N&offset=N&agency=X | List solicitations |
| GET | /solicitations/{id} | Single solicitation |
| POST | /solicitations/scrape | Trigger background scrape |
| GET | /solicitations/scrape/status | Scrape job status |
| GET | /solicitations/{id}/alignment | Alignment scores for a solicitation |
| GET | /capabilities | List capabilities |
| POST | /capabilities | Add new capability |
| POST | /align/run | Trigger background alignment pass |
| GET | /align/status | Alignment job status |
| POST | /projects | Create project from solicitation |
| GET | /projects/{id} | Get project + alignment scores |
| POST | /projects/{id}/generate | Generate draft (body: section_type) |
| GET | /projects/{id}/drafts | List all drafts for project |

## Schema Reference

```
solicitations(id, agency, title, topic_number, description, deadline, url UNIQUE, raw_html, scraped_at)
capabilities(id, name UNIQUE, description, keywords_json)
projects(id, solicitation_id FK, title, status, created_at)
drafts(id, project_id FK, section_type, content, model_version, generated_at)
solicitation_capability_scores(solicitation_id FK, capability_id FK, score, rationale, scored_at)
```

## How to Run

```bash
# Backend
source backend/.venv/bin/activate
uvicorn backend.main:app --reload

# Frontend (Day 5+)
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev
```
