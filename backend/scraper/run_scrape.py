"""
CLI entrypoint for the SBIR.gov scraper.

Usage:
    python backend/scraper/run_scrape.py --max-pages 3
    python backend/scraper/run_scrape.py --max-pages 5 --no-enrich
    python backend/scraper/run_scrape.py --max-pages 2 --max-detail 20
"""
import argparse
import asyncio
import sys
import os

# Allow running from project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.scraper.sbir_scraper import run as scrape
from backend.scraper.dod_scraper import run_sync as scrape_dod_sync
from backend.db.crud import insert_solicitation_if_new
from datetime import datetime

# DOD is fully covered by dod_scraper (dodsbirsttr.mil JSON API with complete descriptions).
# Skipping DOD records from the sbir.gov HTML pass avoids duplicate entries with different URLs.
_SBIR_SKIP_AGENCIES = {"DOD", "Army", "Navy", "Air Force", "Space Force", "DARPA",
                        "OSD", "MDA", "SOCOM", "CBD", "DTRA", "DMEA", "NGA", "NSA", "DIA"}

def parse_date(d_str):
    if not d_str:
        return None
    try:
        dt = datetime.strptime(d_str, "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    # Safely handle dates already in ISO Format (like from DOD scraper)
    if "-" in str(d_str) and len(str(d_str)) == 10:
        return d_str
    return d_str

def build_db_record(record: dict) -> dict:
    return {
        "agency": record.get("agency") or "Unknown",
        "title": record.get("title") or "",
        "topic_number": record.get("topic_number"),
        "description": record.get("description") or "",
        "deadline": parse_date(record.get("deadline")),
        "open_date": parse_date(record.get("open_date")),
        "close_date": parse_date(record.get("close_date")),
        "release_date": parse_date(record.get("release_date")),
        "vehicle_type": record.get("vehicle_type") or "SBIR",
        "branch": record.get("branch"),
        "tpoc_json": record.get("tpoc_json"),
        "url": record.get("url") or "",
        "raw_html": record.get("raw_html"),
        "source": "sbir",
    }

async def main(max_pages: int, enrich: bool, max_detail: int) -> None:
    # Run scrapers concurrently
    loop = asyncio.get_event_loop()
    sbir_task = asyncio.create_task(scrape(max_pages=max_pages, enrich=enrich, max_detail=max_detail))
    # dod_scraper is synchronous (pure urllib) — run in thread executor
    dod_future = loop.run_in_executor(None, scrape_dod_sync)

    sbir_records = await sbir_task
    dod_records = await dod_future
    
    # Filter DOD agency records out of sbir.gov results — dod_scraper covers them with better data
    filtered_sbir = [r for r in sbir_records if r.get("agency", "").strip() not in _SBIR_SKIP_AGENCIES]
    skipped_dod = len(sbir_records) - len(filtered_sbir)
    if skipped_dod:
        print(f"[sbir] Skipped {skipped_dod} DOD-agency records (covered by dod_scraper)")

    records = filtered_sbir + dod_records

    inserted_count = skipped_count = error_count = 0
    for record in records:
        db_rec = build_db_record(record)
        if not db_rec["title"] or not db_rec["url"]:
            continue
        try:
            if insert_solicitation_if_new(db_rec):
                inserted_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"[db] Error inserting {db_rec.get('url')}: {e}")
            error_count += 1

    print(f"\n[done] Inserted {inserted_count} new, {skipped_count} already in db, {error_count} errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SBIR.gov solicitations")
    parser.add_argument("--max-pages", type=int, default=30,
                        help="Number of listing pages to scrape (10 topics each); scraper stops early if a page is empty")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip detail page fetching")
    parser.add_argument("--max-detail", type=int, default=150,
                        help="Max number of detail pages to fetch per run")
    args = parser.parse_args()

    asyncio.run(main(
        max_pages=args.max_pages,
        enrich=not args.no_enrich,
        max_detail=args.max_detail,
    ))
