# HANDOFF

**Last updated:** 2026-04-02 (Sprint 4 complete — Claude)

---

## What Was Built This Session (Claude)

### Sprint 4 features (commits `85cb053`, `e9aae23`, `b348b09`)

**Keyword Filter Infrastructure**
- `search_keywords` table: 607 active terms seeded from all capability profiles + `ssi_sbir_history.csv`
- Source tracked (`capability` / `csv` / `manual`); `active` flag lets you prune without deleting
- Normalization pipeline strips internal program codes (SAMM, FLITES, etc.), sentence fragments, tokens <4 chars
- Full CRUD API: `GET/POST/PATCH/DELETE /keywords`

**Grants.gov Scraper**
- 20 domain-tuned cluster search queries + uncovered active keywords as fallback
- Fetches `synopsisDesc` via `oppId` form-encoded detail endpoint
- Agency normalized on ingest: "U.S. National Science Foundation" → NSF, etc.
- 50 records in DB, all scored; top hits: NASA SAR (0.90), Snow Water 3D (0.85), NRL BAA (0.70)
- Routes: `POST /solicitations/scrape/grants`, `GET /solicitations/scrape/grants/status`

**`vehicle_type` column** — SBIR / STTR / BAA / OTA / Grant on every solicitation

**Watch List**
- `watched` boolean on solicitations + `PATCH /solicitations/{id}/watch`
- Star column in the list table (optimistic toggle)
- "Saved" tab — shows only watched items, respects all filters, expires included

**Dashboard improvements**
- Profile-aware: reads `profile_id` from query param, sourced from `localStorage`
- Each section sorted by `top_alignment_score` descending
- Cards show top 1-3 capability match badges (green ≥0.70 / yellow ≥0.40 / gray)
- Card border color signals overall strength at a glance

**Agency + Branch differentiation**
- `branch` column: DOD component from API (`component` field) — Army, Navy, Air Force, Space Force, DARPA, MDA, SOCOM, CBD, DTRA, DMEA
- `tpoc_json` column: JSON array of `{name, email, phone}`, respecting `emailDisplay`/`phoneDisplay` API flags
- 24 current-cycle DOD topics re-scraped with live branch + TPOC
- 20 historical records backfilled via topic code prefix map
- 130 old SBIR.gov records with no topic number remain `branch=NULL`
- Frontend agency column shows branch when set; TPOC column shows name as `mailto:` link

**Bug fixes**
- `build_db_record` was missing `vehicle_type` — would crash UI-triggered SBIR scrapes
- Default sort changed to `alignmentDesc` (was "Newest Scraped")
- Agency filter dropdown expanded: NIH, NOAA, DOI added

---

## Current State

### DB Snapshot
| Metric | Value |
|--------|-------|
| Total solicitations | 224 |
| SBIR | 173 |
| STTR | 1 |
| Grant | 50 |
| Scored | 224 (100%) |
| With branch | 44 |
| With TPOC | 15 |
| Active keywords | 607 |

### Profiles
| Profile | Capabilities |
|---------|-------------|
| Cory Garms (id=1) | 11 |
| Spectral Sciences (id=5) | 10 |

### Top alignment scores (live)
| Score | Agency/Branch | Title |
|-------|--------------|-------|
| 1.00 | DOD | Autonomous UAS ISR |
| 0.90 | NASA | ROSES25 SAR Mission Data |
| 0.90 | DOD | Symbiotic UAS Delivery System |
| 0.90 | USDA | Forests and Related Resources |
| 0.90 | DOD | Visual Position/Navigation (Computer Vision) |

---

## How to Run

### Backend
```bash
cd /home/cgarms/Projects/proposal_pilot
source backend/.venv/bin/activate
uvicorn backend.main:app --reload
# http://localhost:8000/docs
```

### Frontend
```bash
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev
# http://localhost:5173
```

### Refresh SBIR/DOD data
```bash
source backend/.venv/bin/activate
python backend/scraper/run_scrape.py --max-pages 5 --max-detail 50
python -c "from backend.capabilities.aligner import run_alignment; run_alignment()"
```

### Run Grants.gov scrape (full)
```bash
# Via API (runs in background):
curl -X POST http://localhost:8000/solicitations/scrape/grants -H 'Content-Type: application/json' -d '{"max_results": 200}'
# Then score:
curl -X POST 'http://localhost:8000/align/run?include_expired=true'
```

### Add/manage search keywords
```bash
# List active keywords
curl http://localhost:8000/keywords?active_only=true

# Add a manual keyword
curl -X POST http://localhost:8000/keywords -H 'Content-Type: application/json' -d '{"keyword": "synthetic aperture radar"}'

# Deactivate a noisy keyword (get id from list first)
curl -X PATCH 'http://localhost:8000/keywords/42?active=false'
```

### Re-seed keywords (after adding new capabilities)
```bash
python -m backend.scraper.seed_keywords
```

---

## Full API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /dashboard?profile_id=1 | Lifecycle buckets, sorted by alignment |
| GET | /solicitations | List (filter, sort, paginate, watched_only) |
| GET | /solicitations/{id} | Single solicitation |
| PATCH | /solicitations/{id}/watch?watched=true | Toggle watch |
| POST | /solicitations/scrape | Trigger SBIR/DOD background scrape |
| GET | /solicitations/scrape/status | SBIR scrape status |
| POST | /solicitations/scrape/grants | Trigger Grants.gov scrape |
| GET | /solicitations/scrape/grants/status | Grants scrape status |
| GET | /profiles | List profiles |
| POST | /profiles | Create profile |
| GET | /capabilities?profile_id=X | List capabilities |
| POST | /capabilities | Add capability |
| GET | /keywords?active_only=true | List search keywords |
| POST | /keywords | Add keyword |
| PATCH | /keywords/{id}?active=false | Toggle active |
| DELETE | /keywords/{id} | Hard delete |
| POST | /align/run?include_expired=true | Global alignment pass |
| GET | /align/status | Alignment job status |
| GET | /solicitations/{id}/alignment | Scores for a solicitation |
| POST | /solicitations/{id}/align | Re-run alignment (single) |
| POST | /projects | Create project |
| GET | /projects/{id} | Get project + scores |
| POST | /projects/{id}/generate | Generate draft (tone, focus_area) |
| GET | /projects/{id}/drafts | List drafts |
| PATCH | /projects/{id}/drafts/{draft_id} | Update draft content |
| GET | /projects/{id}/drafts/{draft_id}/export/pdf | Download PDF |
| GET | /projects/{id}/drafts/{draft_id}/export/docx | Download DOCX |

---

## Sprint 5 Plan (Next 5 Days)

Ordered by value-to-effort ratio.

### Day 1 — SOTA Caching + Draft Revision History UI
Two quick wins carried over from Sprint 4 backlog. Zero new concepts, just filling in gaps.

**SOTA caching** (`backend/rag/sota.py`):
- Add `sota_cache` table: `(solicitation_id, query, papers_json, fetched_at)` with 7-day TTL check
- Before every arXiv call, check cache by solicitation_id; return cached papers if fresh
- Eliminates redundant fetches on repeated draft generation for the same topic
- Impact: ~2s faster draft gen, near-zero arXiv cost for re-runs

**Draft revision history UI** (`frontend/src/views/DraftEditor.jsx`):
- The sidebar already lists drafts by timestamp; add: section_type badge, char count
- Add a simple diff view between the selected draft and the previous one using a unified diff endpoint
- Backend: `GET /projects/{id}/drafts/{draft_id}/diff?against={other_id}` using Python `difflib`

---

### Day 2 — Keyword Management UI
607 active keywords is too many to manage via raw API calls. A simple UI page lets you
prune noise, add domain terms, and see which source each keyword came from.

**Backend**: already complete (`/keywords` CRUD).

**Frontend** — new view `frontend/src/views/Keywords.jsx`:
- Table: keyword, source badge (capability / csv / manual), active toggle switch
- Search/filter bar to find terms quickly
- "Add keyword" inline form at the top
- Add route `/keywords` to `App.jsx` and link in NavBar

This is needed before running a full 200-result Grants.gov scrape — gives you the ability
to deactivate irrelevant terms (e.g. biomedical NSF terms) that are generating noise.

---

### Day 3 — SAM.gov Scraper (BAAs and OTAs)
SAM.gov Opportunities API is public and key-free at the base tier (10 req/min).

```
GET https://api.sam.gov/opportunities/v2/search
  ?api_key=REPLACE_OR_OMIT
  &ptype=r  (solicitation type: r=sources sought, k=combined synopsis, p=pre-solicitation)
  &keywords=lidar+remote+sensing
  &active=Yes
  &limit=25
```

Strategy:
- Same keyword-cluster approach as Grants.gov (use `get_all_keywords(active_only=True)`)
- Filter by `ptype=k` (combined synopsis = BAA-equivalent) and `ptype=p` (pre-solicitation)
- `vehicle_type = 'BAA'` or `'OTA'` based on `type` field in response
- Upsert via existing `upsert_solicitation`
- Route: `POST /solicitations/scrape/sam`, `GET /solicitations/scrape/sam/status`

If the key-free tier proves rate-limited, fall back to the daily bulk CSV extract
(posted at `https://api.sam.gov/opportunities/v2/extracts`).

---

### Day 4 — Solicitation Detail Page Improvements
The detail page (`SolicitationDetail.jsx`) was built in Sprint 1 and hasn't been touched since.
It needs to reflect the new data fields added in Sprints 3–4.

Items to add:
- **Branch badge** next to agency (e.g. `DOD / Army` with a colored chip)
- **Vehicle type badge** (`SBIR`, `Grant`, `BAA`) in the header
- **TPOC card** — name, email link, phone if public; visible at top of page, not buried
- **Watch star** — same toggle as the list view, so you can star from the detail page
- **Keyword chips** from `keywords_extra` / `tech_areas` (already in DOD scraper output, not surfaced)

---

### Day 5 — User Authentication (JWT)
Needed before sharing the app with a second person. The schema is already multi-tenant
(profiles have FKs that can be extended).

- Add `users` table: `id, email, hashed_password, created_at`
- Add `user_id` FK to `profiles`
- JWT auth via `python-jose` + `passlib[bcrypt]`; FastAPI `Depends` on protected routes
- Login/register endpoints: `POST /auth/register`, `POST /auth/login` → returns JWT
- Frontend: login page, store token in `localStorage`, attach as `Authorization: Bearer` header
- Profiles and capabilities scoped to `user_id` — other users cannot see your data

Leave scrape endpoints public (or protected by a simple admin flag) since they're
triggered manually and don't expose PII.

---

## Open Questions for Next Session

1. **SAM.gov**: Key-free public tier vs. requesting a free API key from SAM.gov?
   A key allows 100 req/min vs. ~10 without — worth the 5-minute registration.

2. **Keyword pruning**: Before running the full 200-result Grants.gov scrape, review
   the keyword list via the new Keywords UI (Day 2) to deactivate biomedical/irrelevant terms.

3. **Spectral Sciences profile alignment**: The Spectral Sciences profile (id=5) capabilities
   were seeded but alignment has not been run against the full 224-solicitation corpus.
   Run: `POST /align/run?include_expired=true` with profile_id context once the aligner
   supports per-profile runs (currently scores all capabilities in DB simultaneously).

4. **Authentication scope**: Single user (you) or immediately multi-user (e.g., share with
   a colleague at Spectral Sciences)? Affects whether Day 5 is worth the effort now.
