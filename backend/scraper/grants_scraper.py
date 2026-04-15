"""
Grants.gov scraper — searches opportunities matching active search_keywords.

Strategy:
- Loads active keywords from DB, groups into search queries by capability cluster
- Calls Grants.gov search API (no key required)
- Fetches synopsis description for each unique result via the detail endpoint
- Upserts into solicitations with vehicle_type derived from fundingInstruments

Usage (standalone):
    python -m backend.scraper.grants_scraper [--max-results N]
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# Maps Grants.gov full agency names to the short codes used in the rest of the app.
# Keys are lowercase. Unmatched agencies fall through as-is.
_AGENCY_CODES = {
    "u.s. national science foundation": "NSF",
    "national science foundation": "NSF",
    "national institutes of health": "NIH",
    "nasa headquarters": "NASA",
    "national aeronautics and space administration": "NASA",
    "office of science": "DOE",
    "department of energy": "DOE",
    "forest service": "USDA",
    "natural resources conservation service": "USDA",
    "geological survey": "DOI",
    "bureau of reclamation": "DOI",
    "health resources and services Administration": "HHS",
    "health resources and services administration": "HHS",
    "darpa": "DARPA",
    "darpa - biological technologies office": "DARPA",
    "naval research laboratory": "DOD",
    "nswc dahlgren": "DOD",
    "nswc crane - n00164": "DOD",
    "munitions directorate": "DOD",
    "acc apg - natick": "DOD",
    "air force -- research lab": "DOD",
    "dept of the army -- materiel command": "DOD",
    "engineer research and development center": "DOD",
    "department of defense": "DOD",
    "doc noaa - era production": "NOAA",
    "noaa": "NOAA",
}


def _normalize_agency(raw: str) -> str:
    return _AGENCY_CODES.get(raw.strip().lower(), raw.strip())


SEARCH_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search/"
DETAIL_URL = "https://apply07.grants.gov/grantsws/rest/opportunity/details"
GRANTS_BASE = "https://www.grants.gov/search-results-detail"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text).strip()


def _post_json(url: str, payload: dict, timeout: int = 20) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _post_form(url: str, payload: dict, timeout: int = 20) -> dict:
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _build_search_queries(keywords: list[str]) -> list[str]:
    """
    Group keywords into ~20 focused multi-term queries.
    Each query is a short phrase that Grants.gov full-text-searches against titles
    and synopsis text.  Fewer, richer queries beat 607 single-keyword calls.
    """
    # Hard-coded topic clusters that map well to SSI / Cory Garms domain.
    # Any active keyword not captured by these clusters gets appended as
    # individual 1-term queries (capped at MAX_TAIL).
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
        "precision agriculture crop monitoring NDVI",
        "computer vision object detection image segmentation",
        "CubeSat satellite payload on-orbit spaceborne",
        "radiative transfer spectral signature plume",
        "physics-informed machine learning anomaly detection",
        "geospatial GIS spatial analysis mapping",
        "wavefront sensing optical aberration",
        "multispectral imaging change detection surveillance",
    ]

    # Supplement with any active DB keywords not already covered
    covered = set()
    for q in CLUSTERS:
        covered.update(q.lower().split())

    kw_set = set(k.lower() for k in keywords)
    uncovered = sorted(kw_set - covered)

    MAX_TAIL = 30  # cap standalone keyword queries
    tail = uncovered[:MAX_TAIL]

    return CLUSTERS + tail


def _parse_vehicle_type(instruments: list[dict] | None) -> str:
    if not instruments:
        return "Grant"
    codes = {i.get("code", "").upper() for i in instruments}
    if "CA" in codes or "B" in codes:
        return "Grant"
    if "G" in codes:
        return "Grant"
    return "Grant"  # Grants.gov is grants-only; subtype is in CFDA/category


def _parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    # Grants.gov dates: "Sep 30, 2026 12:00:00 AM EDT" or "03/01/2024"
    cleaned = raw.split(" EDT")[0].split(" EST")[0].strip()
    for fmt in ("%b %d, %Y %I:%M:%S %p", "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def search_opportunities(query: str, rows: int = 25) -> list[dict]:
    payload = {
        "keyword": query,
        "oppStatuses": "posted|forecasted",
        "rows": rows,
        "startRecordNum": 0,
    }
    try:
        data = _post_json(SEARCH_URL, payload)
        return data.get("oppHits", [])
    except Exception as e:
        print(f"  [search error] '{query}': {e}")
        return []


def fetch_detail(opp_id: str) -> dict:
    try:
        data = _post_form(DETAIL_URL, {"oppId": opp_id})
        synopsis = data.get("synopsis", {})
        instruments = synopsis.get("fundingInstruments", [])
        desc_html = synopsis.get("synopsisDesc", "") or ""
        return {
            "description": _strip_html(desc_html)[:8000],
            "close_date": _parse_date(synopsis.get("responseDate")),
            "open_date": _parse_date(synopsis.get("postingDate")),
            "vehicle_type": _parse_vehicle_type(instruments),
        }
    except Exception as e:
        print(f"  [detail error] id={opp_id}: {e}")
        return {"description": None, "close_date": None, "open_date": None, "vehicle_type": "Grant"}


def run_grants_scrape(max_results: int = 200, delay: float = 0.5) -> dict:
    from backend.db.crud import get_all_keywords, insert_solicitation_if_new

    keywords = [k["keyword"] for k in get_all_keywords(active_only=True)]
    queries = _build_search_queries(keywords)

    seen_ids: set[str] = set()
    hits: list[dict] = []

    print(f"Running {len(queries)} search queries (max_results={max_results})...")
    for query in queries:
        if len(hits) >= max_results:
            break
        results = search_opportunities(query)
        new = [r for r in results if r["id"] not in seen_ids]
        seen_ids.update(r["id"] for r in new)
        hits.extend(new)
        print(f"  '{query[:50]}' → {len(results)} results, {len(new)} new (total {len(hits)})")
        time.sleep(delay)

    hits = hits[:max_results]
    print(f"\nFetching details for {len(hits)} opportunities...")

    persisted = skipped = errors = 0
    for opp in hits:
        opp_id = str(opp["id"])
        detail = fetch_detail(opp_id)
        time.sleep(delay)

        # Prefer close_date from search result if detail is missing it
        close = detail["close_date"] or _parse_date(opp.get("closeDate"))
        open_ = detail["open_date"] or _parse_date(opp.get("openDate"))

        record = {
            "agency": _normalize_agency(opp.get("agency") or opp.get("agencyCode") or "Unknown"),
            "title": opp.get("title", ""),
            "topic_number": opp.get("number", ""),
            "description": detail["description"] or opp.get("title", ""),
            "deadline": close,
            "open_date": open_,
            "close_date": close,
            "release_date": None,
            "vehicle_type": detail["vehicle_type"],
            "branch": None,
            "tpoc_json": None,
            "url": f"{GRANTS_BASE}/{opp_id}",
            "raw_html": None,
            "source": "grants",
        }

        try:
            if insert_solicitation_if_new(record):
                persisted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  [insert error] {opp.get('title', opp_id)}: {e}")
            errors += 1

    print(f"\nDone. Inserted: {persisted} new, {skipped} already in db, Errors: {errors}")
    return {"inserted": persisted, "skipped_existing": skipped, "errors": errors, "queries_run": len(queries)}


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from backend.database import init_db
    init_db()

    max_r = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    run_grants_scrape(max_results=max_r)
