"""
SAM.gov Contract Opportunities bulk CSV importer.

Reads the full extract from sam.gov/data-services (SAM_ContractOpportunitiesFull.csv),
filters to relevant opportunity types, keyword-matches against active search_keywords,
and upserts results into the solicitations table.

Usage (standalone):
    python -m backend.scraper.sam_csv_parser path/to/SAM_ContractOpportunitiesFull.csv
"""
import csv
import json
import re
from pathlib import Path
from datetime import date, datetime

# Opportunity types we care about — skip awards, mods, justifications
_KEEP_TYPES = {
    "Combined Synopsis/Solicitation",
    "Solicitation",
    "Presolicitation",
    "Sources Sought",
    "Special Notice",
}

_AGENCY_MAP = {
    "dept of defense": "DOD",
    "department of defense": "DOD",
    "dept of the army": "DOD",
    "dept of the navy": "DOD",
    "dept of the air force": "DOD",
    "defense logistics agency": "DOD",
    "defense advanced research projects agency": "DARPA",
    "defense advanced research projects agency  (darpa)": "DARPA",
    "national aeronautics and space administration": "NASA",
    "nasa": "NASA",
    "national science foundation": "NSF",
    "energy, department of": "DOE",
    "dept of energy": "DOE",
    "agriculture, department of": "USDA",
    "interior, department of the": "DOI",
    "health and human services, department of": "HHS",
    "homeland security, department of": "DHS",
    "veterans affairs, department of": "VA",
    "general services administration": "GSA",
    "commerce, department of": "DOC",
    "transportation, department of": "DOT",
    "justice, department of": "DOJ",
    "state, department of": "State",
    "environmental protection agency": "EPA",
    "national oceanic and atmospheric administration": "NOAA",
}

_BRANCH_MAP = {
    "dept of the army": "Army",
    "dept of the navy": "Navy",
    "dept of the air force": "Air Force",
    "defense advanced research projects agency  (darpa)": "DARPA",
    "defense advanced research projects agency (darpa)": "DARPA",
    "missile defense agency (mda)": "MDA",
    "us special operations command (ussocom)": "SOCOM",
    "defense intelligence agency (dia)": "DIA",
    "national geospatial-intelligence agency (nga)": "NGA",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text or "").strip()


def _normalize_agency(dept: str, subtier: str) -> str:
    key = subtier.strip().lower()
    if key in _AGENCY_MAP:
        return _AGENCY_MAP[key]
    key = dept.strip().lower()
    return _AGENCY_MAP.get(key, dept.strip() or "Unknown")


def _extract_branch(dept: str, subtier: str) -> str | None:
    key = subtier.strip().lower()
    return _BRANCH_MAP.get(key)


def _parse_date(raw: str) -> str | None:
    if not raw or not raw.strip():
        return None
    # "2026-04-01 23:28:50.703-04" or "2026-05-01T15:00:00-04:00"
    return raw.strip()[:10]


def _parse_vehicle_type(notice_type: str) -> str:
    t = notice_type.strip()
    if t in ("Solicitation", "Combined Synopsis/Solicitation"):
        return "BAA"
    if t == "Presolicitation":
        return "BAA"
    if t == "Sources Sought":
        return "BAA"
    return "BAA"


def _build_tpoc(row: dict) -> str | None:
    contacts = []
    for prefix in ("Primary", "Secondary"):
        name = row.get(f"{prefix}ContactFullname", "").strip()
        email = row.get(f"{prefix}ContactEmail", "").strip()
        phone = row.get(f"{prefix}ContactPhone", "").strip()
        if name or email:
            entry: dict = {}
            if name:
                entry["name"] = name
            if email:
                entry["email"] = email
            if phone:
                entry["phone"] = phone
            contacts.append(entry)
    return json.dumps(contacts) if contacts else None


def _keyword_match(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


def run_sam_csv_import(csv_path: str, max_results: int = 10000) -> dict:
    from backend.db.crud import get_all_keywords, insert_solicitation_if_new

    path = Path(csv_path)
    if not path.exists():
        return {"error": f"File not found: {csv_path}"}

    # Load active keywords; fall back to hardcoded clusters if table is empty
    kw_rows = get_all_keywords(active_only=True)
    keywords = [k["keyword"].lower() for k in kw_rows]
    if not keywords:
        keywords = [
            "hyperspectral", "lidar", "remote sensing", "radar", "infrared",
            "uav", "uas", "drone", "machine learning", "neural network",
            "point cloud", "edge computing", "fpga", "synthetic aperture",
            "computer vision", "satellite", "sensor", "autonomous",
            "geospatial", "multispectral", "detection", "imaging",
        ]

    today = date.today().isoformat()
    matched: list[dict] = []
    skipped_type = 0
    skipped_kw = 0
    skipped_expired = 0
    total = 0

    with open(path, newline="", encoding="cp1252", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            notice_type = row.get("Type", "").strip()
            if notice_type not in _KEEP_TYPES:
                skipped_type += 1
                continue

            title = _strip_html(row.get("Title", ""))
            description = _strip_html(row.get("Description", ""))
            search_text = f"{title} {description[:3000]}".lower()

            if not _keyword_match(search_text, keywords):
                skipped_kw += 1
                continue

            close_date = _parse_date(row.get("ResponseDeadLine"))
            if close_date and close_date < today:
                skipped_expired += 1
                continue

            dept = row.get("Department/Ind.Agency", "")
            subtier = row.get("Sub-Tier", "")
            notice_id = row.get("NoticeId", "").strip()
            link = row.get("Link", "").strip() or (
                f"https://sam.gov/opp/{notice_id}/view" if notice_id else None
            )

            matched.append({
                "agency": _normalize_agency(dept, subtier),
                "title": title,
                "topic_number": row.get("Sol#", "").strip() or None,
                "description": description[:8000],
                "deadline": close_date,
                "open_date": _parse_date(row.get("PostedDate")),
                "close_date": close_date,
                "release_date": None,
                "vehicle_type": _parse_vehicle_type(notice_type),
                "branch": _extract_branch(dept, subtier),
                "tpoc_json": _build_tpoc(row),
                "url": link,
                "raw_html": None,
                "source": "sam",
            })

    # Sort newest first, cap at max_results
    matched.sort(key=lambda r: r["open_date"] or "", reverse=True)
    matched = matched[:max_results]

    inserted = skipped_existing = errors = 0
    for record in matched:
        if not record["title"] or not record["url"]:
            continue
        try:
            if insert_solicitation_if_new(record):
                inserted += 1
            else:
                skipped_existing += 1
        except Exception as e:
            print(f"  [insert error] {record['title'][:60]}: {e}")
            errors += 1

    print(
        f"SAM CSV import: {total} rows scanned, {skipped_type} skipped (type), "
        f"{skipped_kw} skipped (no keyword match), {skipped_expired} skipped (expired), "
        f"{len(matched)} matched, {inserted} inserted (new), "
        f"{skipped_existing} skipped (already in db), {errors} errors"
    )
    return {
        "rows_scanned": total,
        "keyword_matches": len(matched),
        "inserted": inserted,
        "skipped_existing": skipped_existing,
        "skipped_expired": skipped_expired,
        "errors": errors,
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from backend.database import init_db
    init_db()
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "SAM_ContractOpportunitiesFull.csv"
    max_r = int(sys.argv[2]) if len(sys.argv) > 2 else 10000
    run_sam_csv_import(csv_file, max_r)
