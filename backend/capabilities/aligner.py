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
from backend.llm.factory import get_llm_client
from backend.llm.base import LLMClient
from backend.db.crud import (
    get_all_solicitations,
    get_all_capabilities,
    upsert_score,
    get_scores_for_solicitation,
    get_scored_pairs,
)
from backend.capabilities.prompts import ALIGNMENT_SYSTEM, ALIGNMENT_USER

KEYWORD_THRESHOLD = 0.05  # min keyword score to trigger LLM API call (~2 keyword hits)
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
    client: LLMClient,
    solicitation: dict,
    capability: dict,
) -> tuple[float, str]:
    """
    Call the configured LLM to get a semantic alignment score and rationale.
    Returns (score: float, rationale: str).
    Falls back to (0.0, 'scoring error: ...') on failure.
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
        raw = client.complete(system=ALIGNMENT_SYSTEM, user=prompt, max_tokens=256)
        data = json.loads(raw)
        score = float(data["score"])
        rationale = str(data["rationale"])
        return round(min(1.0, max(0.0, score)), 3), rationale
    except Exception as e:
        return 0.0, f"scoring error: {e}"


def score_solicitation(
    client: LLMClient,
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

        upsert_score(solicitation["id"], cap["id"], score, rationale, solicitation.get("content_hash") or "")
        results.append({
            "capability_id": cap["id"],
            "capability": cap["name"],
            "score": score,
            "rationale": rationale,
            "api_used": api_used,
        })

    return results


def run_alignment(
    solicitation_ids: list[int] | None = None,
    force_api: bool = False,
    include_expired: bool = False,
    profile_id: int | None = None,
    skip_scored: bool = True,
) -> dict:
    """
    Run alignment for all (or specified) solicitations against all capabilities.

    skip_scored (default True): skip any (solicitation, capability) pair that already
    has a non-zero Claude score. New solicitations and new capabilities are always scored.
    Overridden by force_api=True, which rescores everything unconditionally.
    """
    client = get_llm_client()
    capabilities = get_all_capabilities(profile_id=profile_id)
    if not capabilities:
        return {"error": "No capabilities seeded. Run seed_capabilities.py first."}

    solicitations = get_all_solicitations(limit=10000, exclude_expired=not include_expired)
    if solicitation_ids:
        solicitations = [s for s in solicitations if s["id"] in solicitation_ids]

    # Load existing scored pairs once — O(1) lookup during the loop
    already_scored: set[tuple[int, int]] = set()
    if skip_scored and not force_api:
        already_scored = get_scored_pairs()
        print(f"[aligner] {len(already_scored)} pairs already scored — will skip")

    total = len(solicitations)
    api_calls = skipped = errors = 0

    print(f"[aligner] Scoring {total} solicitations x {len(capabilities)} capabilities...")

    for i, sol in enumerate(solicitations):
        # Filter capabilities to only unscored pairs for this solicitation
        caps_to_score = [
            c for c in capabilities
            if force_api or (sol["id"], c["id"]) not in already_scored
        ]
        if not caps_to_score:
            skipped += 1
            continue
        try:
            results = score_solicitation(client, sol, caps_to_score, force_api=force_api)
            api_calls += sum(1 for r in results if r["api_used"])
        except Exception as e:
            print(f"[aligner] Error on solicitation {sol['id']}: {e}")
            errors += 1

        if (i + 1) % 10 == 0 or (i + 1) == total:
            print(f"[aligner] Progress: {i + 1}/{total} (API calls: {api_calls}, skipped: {skipped})")

    return {
        "solicitations_scored": total - skipped,
        "solicitations_skipped": skipped,
        "capabilities": len(capabilities),
        "api_calls_made": api_calls,
        "errors": errors,
    }
