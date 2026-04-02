"""
DOD SBIR/STTR scraper — hits the dodsbirsttr.mil public JSON API directly.
No Playwright required. The API is unauthenticated and returns all active topics.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime

API_URL = "https://www.dodsbirsttr.mil/topics/api/public/topics/search"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

SEARCH_PARAM = {
    "searchText": None,
    "components": None,
    "programYear": None,
    "solicitationCycleNames": ["openTopics"],
    "releaseNumbers": [],
    "topicReleaseStatus": [591, 592],
    "modernizationPriorities": None,
    "sortBy": "finalTopicCode,asc",
}


def _ts_to_iso(ts) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d")


def _parse_item(item: dict) -> dict:
    c_date = _ts_to_iso(item.get("topicEndDate"))
    return {
        "agency": "DOD",
        "title": item.get("topicTitle", ""),
        "topic_number": item.get("topicCode", ""),
        "description": item.get("topicTitle", ""),  # title fallback; no detail page for DOD
        "deadline": c_date,
        "open_date": _ts_to_iso(item.get("topicStartDate")),
        "close_date": c_date,
        "release_date": _ts_to_iso(item.get("topicPreReleaseStartDate")),
        "url": f"https://www.dodsbirsttr.mil/topics-app/?topicId={item.get('topicId', '')}",
        "raw_html": "",
    }


def _fetch_page(page: int, size: int) -> dict:
    params = urllib.parse.urlencode({
        "searchParam": json.dumps(SEARCH_PARAM),
        "size": size,
        "page": page,
    })
    req = urllib.request.Request(f"{API_URL}?{params}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


async def run(max_pages: int = 1, enrich: bool = False, max_detail: int = 50) -> list[dict]:
    """Async-compatible wrapper for the synchronous urllib fetch."""
    return run_sync()


def run_sync() -> list[dict]:
    print("[dod_scraper] Fetching DOD topics from dodsbirsttr.mil API...")
    results = []
    page = 0
    page_size = 100

    while True:
        try:
            data = _fetch_page(page, page_size)
        except Exception as e:
            print(f"[dod_scraper] API error on page {page}: {e}")
            break

        items = data.get("data") or []
        total = data.get("total", 0)

        for item in items:
            try:
                results.append(_parse_item(item))
            except Exception as e:
                print(f"[dod_scraper] parse error: {e}")

        print(f"[dod_scraper] Page {page}: {len(items)} topics (total reported: {total})")

        if len(results) >= total or not items:
            break
        page += 1

    print(f"[dod_scraper] Successfully extracted {len(results)} DOD topics.")
    return results


if __name__ == "__main__":
    topics = run_sync()
    for t in topics:
        print(f"  {t['topic_number']:28} close={t['close_date']} | {t['title'][:60]}")
