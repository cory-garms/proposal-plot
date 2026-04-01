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
from backend.db.crud import upsert_solicitation


def build_db_record(record: dict) -> dict:
    return {
        "agency": record.get("agency") or "Unknown",
        "title": record.get("title") or "",
        "topic_number": record.get("topic_number"),
        "description": record.get("description") or "",
        "deadline": record.get("deadline"),
        "url": record.get("url") or "",
        "raw_html": record.get("raw_html"),
    }


async def main(max_pages: int, enrich: bool, max_detail: int) -> None:
    records = await scrape(max_pages=max_pages, enrich=enrich, max_detail=max_detail)

    new_count = 0
    error_count = 0
    for record in records:
        db_rec = build_db_record(record)
        if not db_rec["title"] or not db_rec["url"]:
            continue
        try:
            upsert_solicitation(db_rec)
            new_count += 1
        except Exception as e:
            print(f"[db] Error upserting {db_rec.get('url')}: {e}")
            error_count += 1

    print(f"\n[done] Persisted {new_count} solicitations ({error_count} errors)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape SBIR.gov solicitations")
    parser.add_argument("--max-pages", type=int, default=3,
                        help="Number of listing pages to scrape (10 topics each)")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip detail page fetching")
    parser.add_argument("--max-detail", type=int, default=50,
                        help="Max number of detail pages to fetch per run")
    args = parser.parse_args()

    asyncio.run(main(
        max_pages=args.max_pages,
        enrich=not args.no_enrich,
        max_detail=args.max_detail,
    ))
