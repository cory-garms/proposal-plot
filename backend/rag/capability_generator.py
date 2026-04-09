"""
Capability generation from researcher profile text.

Takes extracted text (from ORCID / URL / PDF / DOCX) and calls the
configured LLM to produce a list of structured capability areas.

Returns a list of dicts: [{name, description, keywords}, ...]
ready to be reviewed in the frontend before saving to the DB.
"""
import json
import re
from backend.llm.factory import get_llm_client

SYSTEM = """You are a research profile analyst helping build a capability profile for a federal grant and contract matching system.

Your task: analyze the researcher's profile text and identify their broad technical capability areas. Focus on capabilities relevant to federal R&D solicitations (SBIR, STTR, BAA, grants).

Output rules:
- Return ONLY a valid JSON array — no prose, no markdown, no code fences.
- Each element must have exactly three fields: "name", "description", "keywords"
- "name": short capability label (3-6 words, title case). Use broad domain names, not project-specific titles.
- "description": 2-3 sentences describing the capability area and the types of problems it addresses. Write in plain technical language. Do NOT mention the researcher by name. Describe the capability domain, not specific past projects.
- "keywords": array of 15-25 technical terms, lowercase, no duplicates. Include BOTH specific terms AND their broader parent domains (e.g. include both "hyperspectral imaging" AND "remote sensing", both "lidar" AND "active sensing"). Include synonyms and related terms that would appear in solicitation titles and descriptions.
- Identify 4-8 distinct capability areas. Group related specific skills into broader domains rather than listing many narrow capabilities.
- Prefer breadth over specificity: a capability like "Optical Remote Sensing" is better than "VNIR Reflectance Spectroscopy of Coastal Estuaries."
- Keywords must span the full breadth of the domain, including common federal solicitation terms.
"""

USER_TEMPLATE = """Researcher profile:

{profile_text}

Identify this researcher's technical capability areas for federal R&D proposal matching.
Return a JSON array only."""

MAX_TOKENS = 2048


def generate_capabilities_from_text(profile_text: str) -> list[dict]:
    """
    Call the LLM to extract capability areas from profile text.
    Returns a list of {name, description, keywords} dicts.
    Raises ValueError if the LLM response cannot be parsed.
    """
    llm = get_llm_client()
    user_prompt = USER_TEMPLATE.format(profile_text=profile_text.strip())

    raw = llm.complete(system=SYSTEM, user=user_prompt, max_tokens=MAX_TOKENS)

    # Strip markdown code fences if the model added them despite instructions
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\n\nRaw response:\n{raw[:500]}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array, got {type(data).__name__}")

    capabilities = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        description = str(item.get("description", "")).strip()
        keywords = item.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(k).strip().lower() for k in keywords if str(k).strip()]

        if not name or not description:
            continue

        capabilities.append({
            "name": name,
            "description": description,
            "keywords": keywords,
        })

    if not capabilities:
        raise ValueError("LLM returned no valid capability entries.")

    return capabilities
