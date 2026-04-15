"""
SBIR.gov scraper using httpx + BeautifulSoup.

The site renders server-side, so Playwright is not required.
Playwright fallback is reserved for future agency portals that require JS.

Listing endpoint:  https://www.sbir.gov/topics?status=1&page={n}
Detail endpoint:   https://www.sbir.gov/topics/{id}
"""
import asyncio
import time
import httpx
from backend.scraper.parser import parse_listing_page, parse_detail_page

BASE_URL = "https://www.sbir.gov"
LISTING_URL = BASE_URL + "/topics?status=1&page={page}"
RESULTS_PER_PAGE = 10
REQUEST_DELAY = 0.75  # seconds between requests - be polite

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ProposalPilot/1.0; research bot)",
    "Accept": "text/html,application/xhtml+xml",
}


async def scrape_listings(max_pages: int = 3) -> list[dict]:
    """
    Scrape max_pages listing pages. Returns partial solicitation dicts
    (no detail page data yet).
    """
    all_records: list[dict] = []

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        for page in range(max_pages):
            url = LISTING_URL.format(page=page)
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                print(f"[scraper] HTTP error on listing page {page}: {e}")
                break

            records = parse_listing_page(resp.text)
            if not records:
                print(f"[scraper] No records on page {page}, stopping.")
                break

            all_records.extend(records)
            print(f"[scraper] Page {page}: scraped {len(records)} topics (total: {len(all_records)})")

            if page < max_pages - 1:
                await asyncio.sleep(REQUEST_DELAY)

    return all_records


async def enrich_with_detail(
    records: list[dict],
    max_detail: int | None = None,
) -> list[dict]:
    """
    Fetch detail pages for records that lack a topic_number.
    max_detail caps how many detail fetches are made (None = all).
    """
    to_enrich = [r for r in records if not r.get("topic_number")]
    if max_detail is not None:
        to_enrich = to_enrich[:max_detail]

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        for i, record in enumerate(to_enrich):
            try:
                resp = await client.get(record["url"])
                resp.raise_for_status()
                detail = parse_detail_page(resp.text, record["url"])
                record.update({k: v for k, v in detail.items() if v})
            except httpx.HTTPError as e:
                print(f"[scraper] HTTP error fetching detail {record['url']}: {e}")

            if i < len(to_enrich) - 1:
                await asyncio.sleep(REQUEST_DELAY)

            if (i + 1) % 10 == 0:
                print(f"[scraper] Enriched {i + 1}/{len(to_enrich)} detail pages")

    return records


async def run(max_pages: int = 30, enrich: bool = True, max_detail: int = 150) -> list[dict]:
    """Full scrape pipeline: listings + optional detail enrichment."""
    print(f"[scraper] Starting scrape: max_pages={max_pages}, enrich={enrich}")
    records = await scrape_listings(max_pages)
    if enrich and records:
        print(f"[scraper] Enriching {min(len(records), max_detail)} records with detail pages...")
        records = await enrich_with_detail(records, max_detail=max_detail)
    return records
