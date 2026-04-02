"""
SOTA Validation: pulls related papers from the arXiv API.

Uses only stdlib (urllib, xml.etree) — no new dependencies.
Non-fatal: returns [] on any network or parse failure.
"""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from backend.database import get_connection

CACHE_TTL_DAYS = 7

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}
ABSTRACT_MAX_CHARS = 350


def fetch_papers(query: str, max_results: int = 5) -> list[dict]:
    """
    Query arXiv and return up to max_results structured paper records.
    Returns [] on any failure — never raises.
    """
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f"[sota] arXiv fetch failed: {e}")
        return []

    try:
        root = ET.fromstring(xml_data)
        papers = []
        for entry in root.findall("atom:entry", NS):
            title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
            published = (entry.findtext("atom:published", "", NS) or "")[:4]

            link = ""
            for lnk in entry.findall("atom:link", NS):
                if lnk.get("rel") == "alternate":
                    link = lnk.get("href", "")
                    break

            authors = [
                a.findtext("atom:name", "", NS)
                for a in entry.findall("atom:author", NS)
            ][:3]

            if not title:
                continue

            papers.append({
                "title": title,
                "authors": authors,
                "year": published,
                "abstract": summary[:ABSTRACT_MAX_CHARS],
                "url": link,
            })
        return papers
    except Exception as e:
        print(f"[sota] arXiv parse failed: {e}")
        return []


def fetch_papers_cached(solicitation_id: int, query: str, max_results: int = 5) -> list[dict]:
    """
    Cached wrapper around fetch_papers.
    Returns cached result if < CACHE_TTL_DAYS old; otherwise fetches from arXiv and stores.
    """
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT papers_json FROM sota_cache "
                "WHERE solicitation_id = ? AND fetched_at > datetime('now', ?) "
                "ORDER BY fetched_at DESC LIMIT 1",
                (solicitation_id, f"-{CACHE_TTL_DAYS} days"),
            ).fetchone()
        if row:
            return json.loads(row["papers_json"])
    except Exception as e:
        print(f"[sota] cache read failed: {e}")

    papers = fetch_papers(query, max_results)

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO sota_cache (solicitation_id, query, papers_json) VALUES (?, ?, ?)",
                (solicitation_id, query, json.dumps(papers)),
            )
            conn.commit()
    except Exception as e:
        print(f"[sota] cache write failed: {e}")

    return papers


def build_sota_query(sol: dict, top_caps: list[dict]) -> str:
    """
    Build a targeted arXiv search query from solicitation title + top capability keywords.
    Caps at 10 terms to avoid over-constraining the search.
    """
    terms = []

    # Extract meaningful words from solicitation title (skip short stop-words)
    title_words = [w.strip("(),.:") for w in (sol.get("title") or "").split() if len(w) > 3]
    terms.extend(title_words[:5])

    # Add keywords from the top 2 highest-scoring capabilities
    for cap in top_caps[:2]:
        kws = json.loads(cap.get("keywords_json") or "[]")
        terms.extend(kws[:4])

    # Deduplicate, preserve order
    seen: set[str] = set()
    unique = []
    for t in terms:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            unique.append(t)

    return " ".join(unique[:10])
