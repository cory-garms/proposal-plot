"""
Assembles the RAG context package passed to the draft generator.

Pulls from four sources:
  1. Solicitation record (title, agency, topic_number, description, deadline)
  2. All capability alignment scores for the solicitation
  3. Full capability descriptions + keywords for top-scoring capabilities
  4. arXiv SOTA papers relevant to the solicitation + top capabilities
"""
import json
from backend.db.crud import (
    get_solicitation_by_id,
    get_scores_for_solicitation,
    get_all_capabilities,
)
from backend.rag.sota import fetch_papers, build_sota_query

# Only include capability detail for scores above this threshold
CAPABILITY_DETAIL_THRESHOLD = 0.3
MAX_DESCRIPTION_CHARS = 6000


def build_context(solicitation_id: int) -> dict:
    """
    Return a structured context dict ready for use in prompt templates.

    Keys:
        solicitation   - dict of solicitation fields
        scores         - list of {capability, score, rationale} sorted by score desc
        top_capabilities - list of full capability records for high-scoring caps
        context_text   - pre-formatted string for direct prompt injection
    """
    sol = get_solicitation_by_id(solicitation_id)
    if not sol:
        raise ValueError(f"Solicitation {solicitation_id} not found")

    scores = get_scores_for_solicitation(solicitation_id)

    # Build capability detail lookup
    all_caps = {c["id"]: c for c in get_all_capabilities()}
    top_caps = [
        all_caps[s["capability_id"]]
        for s in scores
        if s["score"] >= CAPABILITY_DETAIL_THRESHOLD and s["capability_id"] in all_caps
    ]

    sota_query = build_sota_query(sol, top_caps)
    sota_papers = fetch_papers(sota_query, max_results=5) if sota_query else []

    context_text = _format_context(sol, scores, top_caps, sota_papers)

    return {
        "solicitation": sol,
        "scores": scores,
        "top_capabilities": top_caps,
        "sota_papers": sota_papers,
        "context_text": context_text,
    }


def _format_context(sol: dict, scores: list[dict], top_caps: list[dict], sota_papers: list[dict] = None) -> str:
    description = (sol.get("description") or "")[:MAX_DESCRIPTION_CHARS]

    lines = [
        "=== SOLICITATION ===",
        f"Title:         {sol.get('title', '')}",
        f"Agency:        {sol.get('agency', '')}",
        f"Topic Number:  {sol.get('topic_number') or 'N/A'}",
        f"Deadline:      {sol.get('deadline') or 'N/A'}",
        f"URL:           {sol.get('url', '')}",
        "",
        "--- Full Description ---",
        description,
        "",
    ]

    if scores:
        lines += ["=== CAPABILITY ALIGNMENT SCORES ==="]
        for s in scores:
            lines.append(
                f"  {s['capability']:22} score={s['score']:.3f}  |  {s['rationale']}"
            )
        lines.append("")

    if top_caps:
        lines += ["=== RELEVANT CAPABILITIES (score >= 0.30) ==="]
        for cap in top_caps:
            keywords = json.loads(cap.get("keywords_json") or "[]")
            lines += [
                f"Capability: {cap['name']}",
                f"Description: {cap['description']}",
                f"Key terms: {', '.join(keywords[:12])}",
                "",
            ]

    if sota_papers:
        lines += ["=== RELEVANT PRIOR ART (arXiv) ==="]
        lines.append("Use these papers to ground technical claims. Cite by author and year.")
        lines.append("")
        for i, p in enumerate(sota_papers, 1):
            authors_str = ", ".join(p["authors"]) if p["authors"] else "Unknown"
            lines += [
                f"[{i}] {p['title']}",
                f"    Authors: {authors_str} ({p['year']})",
                f"    Abstract: {p['abstract']}",
                f"    URL: {p['url']}",
                "",
            ]

    return "\n".join(lines)
