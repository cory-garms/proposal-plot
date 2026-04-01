# HANDOFF

**Last updated:** 2026-04-01 (Day 2 complete)

---

## Current State

Days 1-2 complete. The backend scrapes live SBIR.gov data and exposes it via REST.
20 solicitations are currently in the DB (from a 2-page test scrape).
Frontend is still a stub.

---

## What Was Built (Days 1-2)

- Full backend scaffold: FastAPI, SQLite schema (5 tables), CRUD layer
- SBIR.gov scraper: httpx + BeautifulSoup, two-phase (listing + detail pages)
- REST API: `GET /solicitations`, `GET /solicitations/{id}`, `POST /scrape`, `GET /solicitations/scrape/status`
- Frontend stub: React + Vite + TailwindCSS v4

---

## Start Day 3

### Goal
Score every solicitation against 3 capabilities using keyword pre-filter + Claude API semantic scoring.

### Files to create
- `backend/capabilities/seed_capabilities.py`
- `backend/capabilities/prompts.py`
- `backend/capabilities/aligner.py`
- `backend/routers/capabilities.py`
- Register `capabilities` router in `backend/main.py`

### Capabilities to seed
1. **Remote Sensing** - keywords: SAR, LiDAR, hyperspectral, satellite imagery, EO/IR, radar, multispectral
2. **3D Point Clouds** - keywords: LiDAR, photogrammetry, mesh reconstruction, voxelization, SLAM, point cloud
3. **Edge Computing** - keywords: embedded systems, FPGA, low-latency inference, on-device ML, IoT, edge AI, real-time processing

### Alignment logic (two-pass)
1. Keyword match: score 0-1 based on keyword hits in title + description
2. If keyword_score > 0.2: call Claude API for semantic score (0-1) + one-sentence rationale
3. Store result in `solicitation_capability_scores`

### API key required
Set `ANTHROPIC_API_KEY` in `.env` before running Day 3.
Use model `claude-sonnet-4-6`.

---

## How to Run

```bash
# Backend (from project root)
source backend/.venv/bin/activate
uvicorn backend.main:app --reload

# Scrape more data
python backend/scraper/run_scrape.py --max-pages 5 --max-detail 50

# Frontend (requires Node 20 via fnm)
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev
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

## SBIR.gov Scraper Notes

- Listing URL: `https://www.sbir.gov/topics?status=1&page=N` (10/page, ~22k total)
- Detail URL: `https://www.sbir.gov/topics/{id}`
- Server-side rendered - no Playwright needed
- Dedup: `ON CONFLICT(url)` upsert
- Polite delay: 0.75s between requests
