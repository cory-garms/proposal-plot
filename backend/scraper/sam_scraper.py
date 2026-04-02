"""
SAM.gov Opportunities scraper — searches BAAs and pre-solicitations matching active keywords.

Uses the public SAM.gov Opportunities v2 API (no key required at base tier; 10 req/min).
Set SAM_API_KEY in .env to unlock 100 req/min.

Strategy:
- Same keyword-cluster queries used by grants_scraper
- Filters to ptype=k (combined synopsis/BAA) and ptype=p (pre-solicitation)
- vehicle_type derived from noticeType field
- Upserts via existing upsert_solicitation

Usage (standalone):
    python -m backend.scraper.sam_scraper [--max-results N]
"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime

import os
from backend.config import DB_PATH  # noqa: keep import side-effects

SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
SAM_BASE_URL = "https://sam.gov/opp"

# Rate limit: 10/min without key, 100/min with key
_DEFAULT_DELAY = 6.5   # seconds — conservative for key-free tier
_KEY_DELAY = 0.7       # seconds — with API key

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


def _get_api_key() -> str:
    return os.getenv("SAM_API_KEY", "")


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(raw[:19], fmt[:len(fmt)])
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try simple YYYY-MM-DD prefix
    if len(raw) >= 10 and raw[4] == "-":
        return raw[:10]
    return None


def _vehicle_type(notice_type: str | None) -> str:
    """
    SAM.gov noticeType codes:
      o = Solicitation, k = Combined Synopsis, p = Pre-Solicitation,
      r = Sources Sought, j = Justification, i = Intent to Bundle, s = Special Notice
    BAA-like are 'k' and 'p'; OTA contracts flagged by setAside or description.
    We keep it simple: k/p → BAA, rest → BAA (they're all BAA-adjacent for our use).
    """
    nt = (notice_type or "").lower()
    return "BAA"  # All SAM.gov results are BAA/pre-sol class; OTA distinction requires description parse


def _build_search_queries(keywords: list[str]) -> list[str]:
    """Same domain clusters as grants_scraper, adapted for SAM.gov keyword search."""
    CLUSTERS = [
        "hyperspectral lidar remote sensing",
        "electro-optical infrared sensor",
        "synthetic aperture radar SAR",
        "machine learning neural network target detection",
        "unmanned aerial vehicle UAV UAS drone",
        "hypersonics aerothermodynamics computational fluid dynamics",
        "atmospheric modeling space weather ionosphere",
        "counter-UAS drone detection tracking",
        "3D point cloud SLAM reconstruction",
        "edge computing embedded FPGA real-time",
        "scene generation synthetic data modeling simulation",
        "forest inventory biomass canopy mapping",
        "precision agriculture crop monitoring",
        "computer vision object detection",
        "CubeSat satellite spaceborne sensor",
        "radiative transfer spectral signature",
        "physics-informed machine learning",
        "geospatial mapping spatial analysis",
        "wavefront sensing optical aberration",
        "multispectral imaging change detection surveillance",
    ]
    covered = set()
    for q in CLUSTERS:
        covered.update(q.lower().split())
    kw_set = set(k.lower() for k in keywords)
    uncovered = sorted(kw_set - covered)
    return CLUSTERS + uncovered[:20]


def _search(query: str, ptype: str, limit: int = 25, api_key: str = "") -> list[dict]:
    params: dict = {
        "keywords": query,
        "ptype": ptype,
        "active": "Yes",
        "limit": limit,
        "offset": 0,
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{SAM_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        return data.get("opportunitiesData", []) or []
    except Exception as e:
        print(f"  [SAM search error] '{query}' ptype={ptype}: {e}")
        return []


def run_sam_scrape(max_results: int = 200) -> dict:
    from backend.db.crud import get_all_keywords, upsert_solicitation

    api_key = _get_api_key()
    delay = _KEY_DELAY if api_key else _DEFAULT_DELAY

    keywords = [k["keyword"] for k in get_all_keywords(active_only=True)]
    queries = _build_search_queries(keywords)

    seen_ids: set[str] = set()
    records: list[dict] = []

    print(f"SAM.gov scrape: {len(queries)} queries, max_results={max_results}, delay={delay}s")
    if not api_key:
        print("  (no SAM_API_KEY — key-free tier, 10 req/min)")

    for query in queries:
        if len(records) >= max_results:
            break
        for ptype in ("k", "p"):
            if len(records) >= max_results:
                break
            results = _search(query, ptype, limit=25, api_key=api_key)
            new = [r for r in results if r.get("noticeId") not in seen_ids]
            seen_ids.update(r["noticeId"] for r in new if r.get("noticeId"))
            records.extend(new)
            print(f"  '{query[:45]}' ptype={ptype} → {len(results)} hits, {len(new)} new (total {len(records)})")
            time.sleep(delay)

    records = records[:max_results]
    print(f"\nUpserting {len(records)} SAM.gov opportunities...")

    persisted = errors = 0
    for opp in records:
        title = _strip_html(opp.get("title", ""))
        if not title:
            continue

        notice_id = opp.get("noticeId", "")
        sol_number = opp.get("solicitationNumber") or opp.get("noticeId", "")
        url = f"{SAM_BASE_URL}/{notice_id}/view" if notice_id else None

        description = _strip_html(opp.get("description") or opp.get("title") or "")[:8000]
        close_raw = opp.get("responseDeadLine") or opp.get("archiveDate")
        open_raw = opp.get("postedDate")

        # Derive agency — SAM uses 'organizationHierarchy' or top-level 'fullParentPathName'
        agency_raw = (
            opp.get("organizationHierarchy", [{}])[0].get("name", "")
            if opp.get("organizationHierarchy")
            else opp.get("departmentName") or opp.get("subtierName") or "Unknown"
        )
        agency = _normalize_agency(agency_raw)

        record = {
            "agency": agency,
            "title": title,
            "topic_number": sol_number,
            "description": description,
            "deadline": _parse_date(close_raw),
            "open_date": _parse_date(open_raw),
            "close_date": _parse_date(close_raw),
            "release_date": None,
            "vehicle_type": _vehicle_type(opp.get("type")),
            "branch": None,
            "tpoc_json": _extract_tpoc(opp),
            "url": url,
            "raw_html": None,
        }

        try:
            upsert_solicitation(record)
            persisted += 1
        except Exception as e:
            print(f"  [upsert error] {title[:60]}: {e}")
            errors += 1

    print(f"\nDone. Persisted: {persisted}, Errors: {errors}")
    return {"persisted": persisted, "errors": errors, "queries_run": len(queries)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENCY_CODES = {
    "department of defense": "DOD",
    "dept of defense": "DOD",
    "defense advanced research projects agency": "DARPA",
    "darpa": "DARPA",
    "department of the air force": "DOD",
    "department of the army": "DOD",
    "department of the navy": "DOD",
    "air force research laboratory": "DOD",
    "army research laboratory": "DOD",
    "naval research laboratory": "DOD",
    "office of naval research": "DOD",
    "army research office": "DOD",
    "missile defense agency": "DOD",
    "special operations command": "DOD",
    "national aeronautics and space administration": "NASA",
    "nasa": "NASA",
    "national science foundation": "NSF",
    "dept of energy": "DOE",
    "department of energy": "DOE",
    "department of homeland security": "DHS",
    "department of agriculture": "USDA",
    "dept of agriculture": "USDA",
    "department of the interior": "DOI",
    "national oceanic and atmospheric administration": "NOAA",
}


def _normalize_agency(raw: str) -> str:
    return _AGENCY_CODES.get(raw.strip().lower(), raw.strip() or "Unknown")


def _extract_tpoc(opp: dict) -> str | None:
    """Extract TPOC contact(s) from SAM.gov pointOfContact array."""
    contacts = opp.get("pointOfContact") or []
    tpocs = []
    for c in contacts:
        entry: dict = {}
        if c.get("fullName"):
            entry["name"] = c["fullName"]
        elif c.get("firstName") or c.get("lastName"):
            entry["name"] = f"{c.get('firstName','')} {c.get('lastName','')}".strip()
        if c.get("email"):
            entry["email"] = c["email"]
        if c.get("phone"):
            entry["phone"] = c["phone"]
        if entry.get("name") or entry.get("email"):
            tpocs.append(entry)
    return json.dumps(tpocs) if tpocs else None


if __name__ == "__main__":
    import sys
    from backend.database import init_db
    init_db()
    max_r = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_sam_scrape(max_results=max_r)
