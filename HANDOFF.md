# HANDOFF

**Last updated:** 2026-04-02 (Sprint 5 complete — Claude)

---

## What Was Built This Session (Claude)

### Sprint 5 features

**Day 1 — SOTA Caching**
- `sota_cache(solicitation_id, query, papers_json, fetched_at)` table — 7-day TTL
- `fetch_papers_cached()` in `backend/rag/sota.py` wraps arXiv fetch; cache hit = ~2s faster draft gen
- `context_builder.py` uses cached fetch

**Day 1 — Draft Revision History UI**
- `GET /projects/{id}/drafts/{draft_id}/diff?against={other_id}` — unified diff via `difflib`
- Draft history sidebar: section type badge + character count per entry
- "Diff" toggle button in content area — color-coded line view (green/red/blue)

**Day 2 — Keyword Management UI**
- `backend/routers/keywords.py`: full CRUD (`GET/POST/PATCH/DELETE /keywords`)
- `frontend/src/views/Keywords.jsx`: search/filter bar, source badges, active toggle, inline add, delete
- `/keywords` route + NavBar link

**Day 3 — SAM.gov Scraper**
- `backend/scraper/sam_scraper.py`: 20 domain clusters × `ptype=k,p`; TPOC extraction
- Key-free: 6.5s/req. Set `SAM_API_KEY` in `.env` for 0.7s/req (100 req/min)
- Routes: `POST /solicitations/scrape/sam`, `GET /solicitations/scrape/sam/status`

**Day 4 — Solicitation Detail Improvements**
- `SolicitationDetail.jsx`: agency/branch chip, vehicle type badge, TPOC card, watch star, `navigate(-1)` back

**Day 5 — User Authentication (JWT)**
- `users` table + `profiles.user_id` nullable FK (existing data unaffected)
- `backend/routers/auth.py`: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- HS256 JWT, bcrypt passwords, 72h expiry. `JWT_SECRET` in `.env`
- Protected routes: `POST /projects`, `POST /projects/{id}/generate`, `PATCH /projects/{id}/drafts/{id}`
- Frontend: `Login.jsx`, axios interceptors (attach token, redirect on 401), NavBar "Sign out"

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
| Users | 0 (register at `/login` on first run) |
| SOTA cache entries | 0 (populates on first draft gen) |

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

### First-time setup
```bash
# 1. Start backend
source backend/.venv/bin/activate
uvicorn backend.main:app --reload

# 2. Start frontend
export PATH="$HOME/.fnm:$PATH" && eval "$(fnm env)"
cd frontend && npm run dev

# 3. Open http://localhost:5173/login — register your account
#    (SAM_API_KEY and JWT_SECRET should be set in .env before production use)
```

### Scrape & score
```bash
# SBIR/DOD
python backend/scraper/run_scrape.py --max-pages 5 --max-detail 50

# Grants.gov (background via API — prune keywords first via /keywords UI)
curl -X POST http://localhost:8000/solicitations/scrape/grants -H 'Content-Type: application/json' -d '{"max_results": 200}'

# SAM.gov (key-free, slow — set SAM_API_KEY in .env for full speed)
curl -X POST http://localhost:8000/solicitations/scrape/sam -H 'Content-Type: application/json' -d '{"max_results": 100}'

# Re-score everything
curl -X POST 'http://localhost:8000/align/run?include_expired=true'
```

### Re-seed keywords (after adding new capabilities)
```bash
python -m backend.scraper.seed_keywords
```

---

## Full API Reference

| Method | Path | Auth required | Description |
|--------|------|---------------|-------------|
| POST | /auth/register | No | Create account → JWT |
| POST | /auth/login | No | Login (form) → JWT |
| GET | /auth/me | Yes | Current user |
| GET | /health | No | Health check |
| GET | /dashboard?profile_id=1 | No | Lifecycle buckets |
| GET | /solicitations | No | List (filter, sort, paginate) |
| GET | /solicitations/{id} | No | Single solicitation |
| PATCH | /solicitations/{id}/watch | No | Toggle watch |
| POST | /solicitations/scrape | No | Trigger SBIR/DOD scrape |
| GET | /solicitations/scrape/status | No | SBIR scrape status |
| POST | /solicitations/scrape/grants | No | Trigger Grants.gov scrape |
| GET | /solicitations/scrape/grants/status | No | Grants scrape status |
| POST | /solicitations/scrape/sam | No | Trigger SAM.gov scrape |
| GET | /solicitations/scrape/sam/status | No | SAM scrape status |
| GET | /profiles | No | List profiles |
| POST | /profiles | No | Create profile |
| GET | /capabilities?profile_id=X | No | List capabilities |
| POST | /capabilities | No | Add capability |
| GET | /keywords | No | List keywords |
| POST | /keywords | No | Add keyword |
| PATCH | /keywords/{id}?active= | No | Toggle active |
| DELETE | /keywords/{id} | No | Delete keyword |
| POST | /align/run | No | Global alignment pass |
| GET | /align/status | No | Alignment job status |
| GET | /solicitations/{id}/alignment | No | Scores for a solicitation |
| POST | /solicitations/{id}/align | No | Re-run alignment (single) |
| POST | /projects | **Yes** | Create project |
| GET | /projects/{id} | No | Get project + scores |
| POST | /projects/{id}/generate | **Yes** | Generate draft |
| GET | /projects/{id}/drafts | No | List drafts |
| PATCH | /projects/{id}/drafts/{draft_id} | **Yes** | Update draft content |
| GET | /projects/{id}/drafts/{draft_id}/diff | No | Unified diff between drafts |
| GET | /projects/{id}/drafts/{draft_id}/export/pdf | No | Download PDF |
| GET | /projects/{id}/drafts/{draft_id}/export/docx | No | Download DOCX |

---

## Sprint 6 Plan

Ordered by value-to-effort ratio.

### Day 1 — Scrape Admin UI
Right now all scrape triggers require raw `curl` commands. A single admin page removes that friction.

**Frontend** — new view `frontend/src/views/Admin.jsx`:
- Three scraper cards: SBIR/DOD, Grants.gov, SAM.gov
- Each card: "Run Scrape" button with `max_results` input, live status polling every 5s while running, last-run stats (persisted/errors)
- "Run Alignment" button with status indicator
- `/admin` route + NavBar link (show only when `localStorage.getItem('token')` is set)

**Backend**: no changes needed — all endpoints already exist.

---

### Day 2 — Profile → User Scoping
The `users` table and `profiles.user_id` column exist but aren't enforced. This day wires them.

- One-time migration: `UPDATE profiles SET user_id = (SELECT id FROM users LIMIT 1)` after first registration
- Add `user_id` to `get_all_profiles()` filter: only return profiles where `user_id = current_user.id`
- Protect `POST/PATCH /profiles` and `POST/PATCH /capabilities` with `require_user`
- Frontend: after login, refresh profile list (currently stale if a second user is added)
- Leave solicitations and drafts unscoped for now — no PII, and shared access is useful

---

### Day 3 — Capability Management UI
Capabilities can only be added/edited via seed scripts or raw API. A UI removes this bottleneck.

**Frontend** — new view `frontend/src/views/Capabilities.jsx`:
- List cards per capability: name, description, keyword chips (first 8), edit/delete
- "Add capability" form: name, description, keywords (comma-separated)
- On save: re-seed keywords from capability (`POST /keywords` for each new keyword) and trigger alignment

**Backend**: `PATCH /capabilities/{id}` and `DELETE /capabilities/{id}` endpoints needed (currently only `POST`).

---

### Day 4 — Per-Profile Alignment
The aligner (`backend/capabilities/aligner.py`) scores all capabilities across all profiles in one pass. This means running alignment for Spectral Sciences also re-scores Cory Garms capabilities.

- Add `profile_id` query param to `POST /align/run?profile_id=1`
- In `run_alignment()`, filter capabilities by profile before scoring
- In Admin UI (Day 1), expose profile selector for the alignment run button

---

### Day 5 — SAM.gov Test Run + Dedup Audit
Before merging SAM results into the main workflow, validate data quality.

- Run `POST /solicitations/scrape/sam` with `max_results=50` (key-free, ~6 min)
- Inspect results via `/solicitations?agency=DOD&sort_by=alignment&sort_desc=true`
- Check for title/description quality — SAM descriptions are often short; add fallback to `raw_html` parse if `description` is under 200 chars
- Add `source` column to `solicitations` table: `sbir`, `grants`, `sam` — useful for filtering and debugging

---

## Open Questions for Next Session

1. **JWT_SECRET**: Set a real secret in `.env` before using the app with real data:
   ```bash
   echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >> .env
   ```

2. **SAM_API_KEY**: Free registration at `https://sam.gov/profile/details` unlocks 100 req/min vs 10. Worth the 5-minute signup before running the full SAM scrape.

3. **Keyword pruning**: 607 keywords includes some biomedical/unrelated terms from `ssi_sbir_history.csv`. Use the `/keywords` UI to deactivate noise before running a full 200-result Grants.gov scrape.

4. **Profile scoping decision**: Should Spectral Sciences profile data be hidden from other users (once multi-user is live), or is shared read access acceptable within your team?

5. **Profile alignment gap**: Spectral Sciences (id=5) capabilities have not been aligned against the full 224-solicitation corpus since the profile was created. Run:
   ```bash
   curl -X POST 'http://localhost:8000/align/run?include_expired=true'
   ```
