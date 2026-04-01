# HANDOFF

**Last updated:** 2026-04-01 (Sprint complete - all 5 days done)

---

## Current State

MVP is complete and fully functional. Backend + frontend end-to-end demo works.

- 98 solicitations scraped and scored
- 3 capabilities seeded (Remote Sensing, 3D Point Clouds, Edge Computing)
- 2 projects created with Technical Volume drafts (16-17k chars each)
- React frontend: 3 views, fully wired to backend

---

## How to Run

### Backend
```bash
cd /home/cgarms/Projects/proposal_pilot
source backend/.venv/bin/activate
uvicorn backend.main:app --reload
# http://localhost:8000/docs  <- interactive API docs
```

### Frontend
```bash
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev
# http://localhost:5173
```

### Seed + scrape fresh data
```bash
python -m backend.capabilities.seed_capabilities          # only needed once
python backend/scraper/run_scrape.py --max-pages 10 --max-detail 100
python -c "from backend.capabilities.aligner import run_alignment; run_alignment()"
```

---

## Good Demo Solicitations

| ID | Title | Top Score | Capability |
|----|-------|-----------|------------|
| 81 | Cognitive Mapping for Counter-WMD (DTRA254-002) | 0.850 | 3D Point Clouds |
| 103 | Shop Floor Human Detection (AF254-D0823) | 0.850 | 3D Point Clouds |
| 50 | Real-Time Detection and Tracking | 0.700 | Edge Computing |
| 79 | PEO SOF Visual Augmentation Systems | 0.700 | Edge Computing |

---

## Next Sprint Ideas (Post-MVP)

- **More agencies**: USDA, NASA, NSF solicitation scrapers
- **Alignment re-run on demand**: per-solicitation re-score button in UI
- **Draft editing**: inline editing of generated sections, save revisions
- **Export**: PDF or DOCX export of full Technical Volume
- **Agency filter**: filter solicitation list by agency in UI
- **Deadline alerts**: flag solicitations with deadlines within 30 days
- **SOTA validation**: auto-pull related papers from arXiv/Semantic Scholar to ground technical claims

---

## Full API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /solicitations?limit=N&offset=N&agency=X | List solicitations |
| GET | /solicitations/{id} | Single solicitation |
| POST | /solicitations/scrape | Trigger background scrape |
| GET | /solicitations/scrape/status | Scrape job status |
| GET | /solicitations/{id}/alignment | Alignment scores |
| GET | /capabilities | List capabilities |
| POST | /capabilities | Add capability |
| POST | /align/run | Trigger alignment pass |
| GET | /align/status | Alignment job status |
| POST | /projects | Create project |
| GET | /projects/{id} | Get project + scores |
| POST | /projects/{id}/generate | Generate draft section |
| GET | /projects/{id}/drafts | List drafts |

## Schema

```
solicitations(id, agency, title, topic_number, description, deadline, url UNIQUE, raw_html, scraped_at)
capabilities(id, name UNIQUE, description, keywords_json)
projects(id, solicitation_id FK, title, status, created_at)
drafts(id, project_id FK, section_type, content, model_version, generated_at)
solicitation_capability_scores(solicitation_id FK, capability_id FK, score, rationale, scored_at)
```
