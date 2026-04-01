"""
HTML parsers for SBIR.gov listing and detail pages.

Listing page:  /topics?status=1&page=N  (10 results per page)
Detail page:   /topics/{id}
"""
import re
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://www.sbir.gov"


def parse_listing_page(html: str) -> list[dict]:
    """
    Parse a /topics listing page and return a list of partial solicitation dicts.
    Each dict has: title, url, status, agency, release_date, open_date, close_date,
                   description, tags
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Topics are h3 elements whose first child is a link to /topics/{id}
    headings = [
        h for h in soup.find_all("h3")
        if h.find("a") and "/topics/" in h.find("a").get("href", "")
    ]

    for h in headings:
        link = h.find("a")
        title = link.get_text(strip=True)
        url = BASE_URL + link["href"]

        # The metadata <p> immediately follows the h3
        meta_p = h.find_next_sibling("p")
        status, release_date, open_date, close_date = _parse_meta_p(meta_p)

        # The grid-row div follows the meta <p>
        grid_div = meta_p.find_next_sibling("div") if meta_p else None
        agency, description, tags = _parse_grid_div(grid_div)

        results.append({
            "title": title,
            "url": url,
            "topic_number": None,     # filled by detail page
            "agency": agency,
            "description": description,
            "deadline": close_date,
            "release_date": release_date,
            "open_date": open_date,
            "close_date": close_date,
            "status": status,
            "tags": tags,
            "raw_html": None,
        })

    return results


def _parse_meta_p(p: Tag | None) -> tuple[str, str, str, str]:
    """Extract status, release_date, open_date, close_date from the metadata <p>."""
    if p is None:
        return "", "", "", ""

    text = p.get_text(separator="|", strip=True)

    # Status is the first badge span
    status_span = p.find("span")
    status = status_span.get_text(strip=True) if status_span else ""

    release_date = _extract_date_after(text, "Release Date:")
    open_date = _extract_date_after(text, "Open Date:")
    close_date = _extract_date_after(text, "Close Date:")

    return status, release_date, open_date, close_date


def _extract_date_after(text: str, label: str) -> str:
    """Pull the date string that appears after a label in pipe-separated text."""
    if label not in text:
        return ""
    parts = text.split("|")
    for i, part in enumerate(parts):
        if label in part and i + 1 < len(parts):
            return parts[i + 1].strip()
    return ""


def _parse_grid_div(div: Tag | None) -> tuple[str, str, list[str]]:
    """Extract agency, description snippet, and tags from the grid-row div."""
    if div is None:
        return "", "", []

    # Agency from img alt text, e.g. "Seal of the Agency: DOD"
    img = div.find("img", alt=True)
    agency = ""
    if img:
        alt = img["alt"]
        match = re.search(r"Agency:\s*(.+)", alt)
        agency = match.group(1).strip() if match else alt.strip()

    # Description from the <p class="measure-6"> paragraph
    desc_p = div.find("p", class_="measure-6")
    description = desc_p.get_text(strip=True) if desc_p else ""

    # Tags from the badge paragraphs (SBIR, STTR, BOTH, etc.)
    tag_container = div.find("div", class_="display-inline-flex")
    tags = []
    if tag_container:
        for tp in tag_container.find_all("p"):
            t = tp.get_text(strip=True)
            if t and "Tagged as" not in t:
                tags.append(t)

    return agency, description, tags


def parse_detail_page(html: str, url: str) -> dict:
    """
    Parse a /topics/{id} detail page.
    Returns: topic_number, solicitation_number, agency, full description, raw_html.
    """
    soup = BeautifulSoup(html, "html.parser")
    text_lines = [
        line.strip()
        for line in soup.get_text(separator="\n").splitlines()
        if line.strip()
    ]

    topic_number = _extract_field_value(text_lines, "Topic Number:")
    solicitation_number = _extract_field_value(text_lines, "Solicitation Number:")
    agency = _extract_field_value(text_lines, "Funding Agency")

    # Full description starts after "Description" heading
    description = ""
    try:
        desc_idx = text_lines.index("Description")
        description = "\n".join(text_lines[desc_idx + 1:desc_idx + 80]).strip()
    except ValueError:
        pass

    return {
        "url": url,
        "topic_number": topic_number,
        "solicitation_number": solicitation_number,
        "agency": agency,
        "description": description,
        "raw_html": html,
    }


def _extract_field_value(lines: list[str], label: str) -> str:
    """Return the line immediately after a label line."""
    for i, line in enumerate(lines):
        if line.startswith(label) and i + 1 < len(lines):
            return lines[i + 1].strip()
    return ""
