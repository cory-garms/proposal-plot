# HANDOFF

**Last updated:** 2026-04-01 (Sprint 3 complete — Claude)

---

## Current State

Sprint 3 added four major features on top of the multi-tenant profile / dashboard foundation from Sprint 2.

### What was built this sprint

**SOTA Validation**
- `backend/rag/sota.py` — queries the arXiv public API using solicitation title + capability keywords. Non-fatal: returns `[]` if arXiv is unreachable.
- `context_builder.py` updated to call SOTA and inject a `=== RELEVANT PRIOR ART (arXiv) ===` block into every draft context.
- `rag/prompts.py` system prompt updated to require citations by `Author et al. (year)` and forbid hallucinated references.

**Inline Draft Editing + Save**
- `PATCH /projects/{id}/drafts/{draft_id}` — validates ownership, rejects empty content, returns updated record.
- `DraftEditor.jsx` — Edit/Save/Cancel toolbar; textarea replaces read-only div in edit mode; "Saved" confirmation on success.

**Export to PDF and DOCX**
- `backend/export/docx_writer.py` — python-docx, parses `##`/`###`/`-` markdown structure, 1.25" margins.
- `backend/export/pdf_writer.py` — ReportLab, matching styles, XML-safe escaping.
- `GET /projects/{id}/drafts/{draft_id}/export/pdf` and `.../export/docx` — both return `Content-Disposition: attachment`.
- PDF and DOCX download links in DraftEditor toolbar (read mode only).

**Draft Settings (Tone + Focus)**
- `GenerateRequest` now accepts `tone` (`technical`/`executive`/`persuasive`) and `focus_area` (`balanced`/`innovation`/`feasibility`/`commercialization`).
- Settings are appended as a modifier block to the user prompt. Zero overhead at defaults.
- Two dropdowns added to the Generate panel in DraftEditor.

**DOD Scraper rewrite**
- Dropped Playwright entirely. New `dod_scraper.py` hits `dodsbirsttr.mil/topics/api/public/topics/search` directly with `urllib` — no browser, no timeouts.
- Was fetching 10 (first page only). Now fetches all 24 active topics with pagination.
- `run_scrape.py` updated to call `run_sync()` via executor.

---

## IMPORTANT: API Credits

The Anthropic API account ran out of credits during Sprint 3 testing. All alignment scores are currently 0.00 (scoring errors). **Top up credits before the demo.** After topping up:

```bash
source backend/.venv/bin/activate
python -c "from backend.capabilities.aligner import run_alignment; run_alignment()"
```

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

### Seed + scrape fresh data
```bash
python -m backend.capabilities.seed_capabilities
python backend/scraper/run_scrape.py --max-pages 5 --max-detail 50
python -c "from backend.capabilities.aligner import run_alignment; run_alignment()"
```

---

## Full API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| GET | /solicitations | List solicitations (filter, sort, paginate) |
| GET | /solicitations/{id} | Single solicitation |
| POST | /solicitations/scrape | Trigger background scrape |
| GET | /solicitations/scrape/status | Scrape job status |
| GET | /dashboard | Lifecycle buckets + agency calendar |
| GET | /profiles | List profiles |
| POST | /profiles | Create profile |
| GET | /capabilities?profile_id=X | List capabilities |
| POST | /capabilities | Add capability |
| POST | /align/run | Global alignment pass |
| GET | /align/status | Alignment job status |
| GET | /solicitations/{id}/alignment | Scores for a solicitation |
| POST | /solicitations/{id}/align | Re-run alignment |
| POST | /projects | Create project |
| GET | /projects/{id} | Get project + scores |
| POST | /projects/{id}/generate | Generate draft (tone, focus_area params) |
| GET | /projects/{id}/drafts | List drafts |
| PATCH | /projects/{id}/drafts/{draft_id} | Update draft content |
| GET | /projects/{id}/drafts/{draft_id}/export/pdf | Download PDF |
| GET | /projects/{id}/drafts/{draft_id}/export/docx | Download DOCX |

## Next Sprint Ideas

- **Expanded scrapers** — USDA, NASA, NSF dedicated portal scrapers
- **DOD topic detail fetch** — currently description = title for DOD topics; a detail page fetch would improve alignment scoring significantly
- **Solicitation watch list** — pin/bookmark solicitations for follow-up
- **User auth** — multi-user support with JWT; currently single-user only
