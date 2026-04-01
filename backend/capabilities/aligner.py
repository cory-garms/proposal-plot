"""
Two-pass capability alignment scorer.

Pass 1 - Keyword match (free, instant):
    Score 0-1 based on keyword hits in title + description.
    Normalized by sqrt(matched) to avoid over-rewarding keyword-stuffed docs.

Pass 2 - Claude API semantic scoring (only if keyword_score > KEYWORD_THRESHOLD):
    Calls Claude with a structured prompt and parses a JSON response.
    Result is stored in solicitation_capability_scores.
"""
import json
import re
import anthropic
from backend.config import ANTHROPIC_API_KEY
from backend.db.crud import (
    get_all_solicitations,
    get_all_capabilities,
    upsert_score,
    get_scores_for_solicitation,
)
from backend.capabilities.prompts import ALIGNMENT_SYSTEM, ALIGNMENT_USER

KEYWORD_THRESHOLD = 0.15  # min keyword score to trigger Claude API call
MODEL = "claude-sonnet-4-6"
MAX_DESC_CHARS = 3000       # truncate long descriptions to control token cost


def keyword_score(text: str, keywords: list[str]) -> float:
    """
    Return 0-1 score based on how many keywords appear in text.
    Case-insensitive whole-word match. Normalized so diminishing returns kick in.
    """
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    hits = sum(
        1 for kw in keywords
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower)
    )
    if hits == 0:
        return 0.0
    # sqrt normalization: 1 hit -> ~0.09, 4 hits -> 0.18, 9 hits -> 0.27, 25 hits -> 0.45
    # scale by 1/sqrt(len(keywords)) so score is relative to vocabulary size
    return min(1.0, (hits ** 0.5) / (len(keywords) ** 0.5))


def semantic_score(
    client: anthropic.Anthropic,
    solicitation: dict,
    capability: dict,
) -> tuple[float, str]:
    """
    Call Claude API to get a semantic alignment score and rationale.
    Returns (score: float, rationale: str).
    Falls back to (0.0, 'API error') on failure.
    """
    description = (solicitation.get("description") or "")[:MAX_DESC_CHARS]
    prompt = ALIGNMENT_USER.format(
        capability_name=capability["name"],
        capability_description=capability["description"],
        title=solicitation.get("title", ""),
        agency=solicitation.get("agency", ""),
        description=description,
    )
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=ALIGNMENT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        score = float(data["score"])
        rationale = str(data["rationale"])
        return round(min(1.0, max(0.0, score)), 3), rationale
    except Exception as e:
        return 0.0, f"scoring error: {e}"


def score_solicitation(
    client: anthropic.Anthropic,
    solicitation: dict,
    capabilities: list[dict],
    force_api: bool = False,
) -> list[dict]:
    """
    Score one solicitation against all capabilities.
    Returns list of score dicts with keys: capability_id, capability, score, rationale, api_used.
    """
    search_text = f"{solicitation.get('title', '')} {solicitation.get('description', '')}"
    results = []

    for cap in capabilities:
        keywords = json.loads(cap.get("keywords_json") or "[]")
        kw_score = keyword_score(search_text, keywords)

        if kw_score > KEYWORD_THRESHOLD or force_api:
            score, rationale = semantic_score(client, solicitation, cap)
            api_used = True
        else:
            score = kw_score
            rationale = f"keyword score {kw_score:.3f} below threshold - no API call"
            api_used = False

        upsert_score(solicitation["id"], cap["id"], score, rationale)
        results.append({
            "capability_id": cap["id"],
            "capability": cap["name"],
            "score": score,
            "rationale": rationale,
            "api_used": api_used,
        })

    return results


def run_alignment(solicitation_ids: list[int] | None = None, force_api: bool = False) -> dict:
    """
    Run alignment for all (or specified) solicitations against all capabilities.
    Returns stats dict.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    capabilities = get_all_capabilities()
    if not capabilities:
        return {"error": "No capabilities seeded. Run seed_capabilities.py first."}

    solicitations = get_all_solicitations(limit=10000)
    if solicitation_ids:
        solicitations = [s for s in solicitations if s["id"] in solicitation_ids]

    total = len(solicitations)
    api_calls = 0
    errors = 0

    print(f"[aligner] Scoring {total} solicitations x {len(capabilities)} capabilities...")

    for i, sol in enumerate(solicitations):
        try:
            results = score_solicitation(client, sol, capabilities, force_api=force_api)
            api_calls += sum(1 for r in results if r["api_used"])
        except Exception as e:
            print(f"[aligner] Error on solicitation {sol['id']}: {e}")
            errors += 1

        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"[aligner] Progress: {i + 1}/{total} (API calls so far: {api_calls})")

    return {
        "solicitations_scored": total,
        "capabilities": len(capabilities),
        "total_scores": total * len(capabilities),
        "api_calls_made": api_calls,
        "errors": errors,
    }
