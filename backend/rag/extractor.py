"""
Text extraction for capability generation.

Supports:
  - ORCID profile URLs  (https://orcid.org/<id>)
  - Generic URLs        (CV pages, lab pages, faculty pages)
  - PDF uploads         (via pymupdf)
  - DOCX uploads        (via python-docx)

Each function returns a plain text string ready to be passed to the LLM.
All functions raise ValueError with a human-readable message on failure.
"""
import io
import json
import re
import urllib.request
import urllib.parse
from typing import BinaryIO
import xml.etree.ElementTree as _ET

import httpx
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# ORCID
# ---------------------------------------------------------------------------

ORCID_ID_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])")


def _strip_xml_tags(text: str) -> str:
    """Remove any residual XML/HTML tags from a string (e.g. <emph> in ORCID titles)."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _extract_orcid_id(url_or_id: str) -> str:
    m = ORCID_ID_RE.search(url_or_id)
    if not m:
        raise ValueError(f"Could not find a valid ORCID ID in: {url_or_id}")
    return m.group(1)


def extract_from_orcid(url_or_id: str) -> str:
    """
    Fetch an ORCID public record and return a structured text summary
    suitable for LLM capability extraction.
    """
    orcid_id = _extract_orcid_id(url_or_id)
    api_url = f"https://pub.orcid.org/v3.0/{orcid_id}/record"

    try:
        req = urllib.request.Request(
            api_url,
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise ValueError(f"Failed to fetch ORCID record: {e}") from e

    lines: list[str] = []

    # Name
    person = data.get("person", {})
    name = person.get("name", {})
    given = name.get("given-names", {}).get("value", "")
    family = name.get("family-name", {}).get("value", "")
    if given or family:
        lines.append(f"Researcher: {given} {family}".strip())

    # Bio
    bio = person.get("biography", {})
    if bio and bio.get("content"):
        lines.append(f"\nBiography:\n{bio['content']}")

    # Keywords
    kw_group = person.get("keywords", {}).get("keyword", [])
    if kw_group:
        kws = [k.get("content", "") for k in kw_group if k.get("content")]
        if kws:
            lines.append(f"\nSelf-reported keywords: {', '.join(kws)}")

    # Employment
    employments = (
        data.get("activities-summary", {})
        .get("employments", {})
        .get("affiliation-group", [])
    )
    if employments:
        lines.append("\nEmployment:")
        for grp in employments:
            for summ in grp.get("summaries", []):
                s = summ.get("employment-summary", {})
                org = s.get("organization", {}).get("name", "")
                role = s.get("role-title", "")
                dept = s.get("department-name", "")
                start = (s.get("start-date") or {}).get("year", {}).get("value", "")
                end_d = s.get("end-date")
                end = end_d.get("year", {}).get("value", "") if end_d else "present"
                parts = [p for p in [role, dept, org] if p]
                period = f" ({start}–{end})" if start else ""
                lines.append(f"  - {', '.join(parts)}{period}")

    # Works / publications
    works_groups = (
        data.get("activities-summary", {})
        .get("works", {})
        .get("group", [])
    )
    if works_groups:
        lines.append("\nPublications:")
        for grp in works_groups:
            for ws in grp.get("work-summary", []):
                title = (ws.get("title", {}).get("title") or {}).get("value", "")
                journal = (ws.get("journal-title") or {}).get("value", "")
                year = (
                    (ws.get("publication-date") or {})
                    .get("year", {})
                    .get("value", "")
                )
                title = _strip_xml_tags(title)
                journal = _strip_xml_tags(journal)
                if title:
                    parts = [title]
                    if journal:
                        parts.append(journal)
                    if year:
                        parts.append(year)
                    lines.append(f"  - {' | '.join(parts)}")
                break  # one summary per group is enough

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generic URL
# ---------------------------------------------------------------------------

def _extract_google_scholar(url: str) -> str:
    """
    Extract researcher profile from Google Scholar.
    Handles https://scholar.google.com/citations?user=...
    """
    try:
        resp = httpx.get(
            url,
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Google Scholar returned HTTP {e.response.status_code}. Try using an ORCID URL instead.") from e
    except Exception as e:
        raise ValueError(f"Failed to fetch Google Scholar profile: {e}") from e

    soup = BeautifulSoup(resp.text, "html.parser")

    lines: list[str] = []

    # Researcher name
    name_el = soup.find(id="gsc_prf_in")
    if name_el:
        lines.append(f"Researcher: {name_el.get_text(strip=True)}")

    # Affiliation and interests
    aff_el = soup.find(class_="gsc_prf_il")
    if aff_el:
        lines.append(f"Affiliation: {aff_el.get_text(strip=True)}")

    interests = soup.find_all(class_="gsc_prf_inta")
    if interests:
        kws = [el.get_text(strip=True) for el in interests]
        lines.append(f"Research interests: {', '.join(kws)}")

    # Publications
    pubs = soup.find_all(class_="gsc_a_tr")
    if pubs:
        lines.append("\nPublications:")
        for pub in pubs[:30]:
            title_el = pub.find(class_="gsc_a_at")
            venue_el = pub.find(class_="gs_gray")
            year_el = pub.find(class_="gsc_a_y")
            if title_el:
                title = title_el.get_text(strip=True)
                venue = venue_el.get_text(strip=True) if venue_el else ""
                year = year_el.get_text(strip=True) if year_el else ""
                parts = [p for p in [title, venue, year] if p]
                lines.append(f"  - {' | '.join(parts)}")

    if len(lines) < 3:
        raise ValueError("Could not extract profile data from Google Scholar. The page may require login or block automated access.")

    return "\n".join(lines)[:12000]


def _extract_researchgate(url: str) -> str:
    """
    Extract researcher profile from ResearchGate.
    Handles https://www.researchgate.net/profile/...
    """
    try:
        resp = httpx.get(
            url,
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 429):
            raise ValueError(
                "ResearchGate blocked automated access. Try pasting your CV/publication list as a PDF or DOCX instead."
            ) from e
        raise ValueError(f"ResearchGate returned HTTP {e.response.status_code}.") from e
    except Exception as e:
        raise ValueError(f"Failed to fetch ResearchGate profile: {e}") from e

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) < 200:
        raise ValueError(
            "ResearchGate returned too little content (likely blocked). "
            "Try uploading your CV or publication list as a PDF instead."
        )

    return cleaned[:12000]


def extract_from_url(url: str) -> str:
    """
    Fetch a web page and return its cleaned text content.
    Supports: ORCID, Google Scholar, ResearchGate, faculty pages, lab pages.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Route to specialized extractors
    if "orcid.org/" in url and ORCID_ID_RE.search(url):
        return extract_from_orcid(url)
    if "scholar.google.com" in url:
        return _extract_google_scholar(url)
    if "researchgate.net" in url:
        return _extract_researchgate(url)

    try:
        resp = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP {e.response.status_code} fetching {url}") from e
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {e}") from e

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove boilerplate elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) < 100:
        raise ValueError("Page returned too little text to extract capabilities from.")

    # Truncate to ~12k chars to stay within LLM context
    return cleaned[:12000]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file (in-memory bytes)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        raise ValueError("PDF support requires pymupdf. Run: pip install pymupdf")

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF: {e}") from e

    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()

    text = "\n".join(pages).strip()
    if len(text) < 100:
        raise ValueError("PDF contains too little extractable text (may be image-only).")

    return text[:12000]


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

def extract_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file (in-memory bytes)."""
    try:
        from docx import Document
    except ImportError:
        raise ValueError("DOCX support requires python-docx. Run: pip install python-docx")

    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Could not open DOCX: {e}") from e

    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if len(text) < 100:
        raise ValueError("DOCX contains too little text.")

    return text[:12000]
