"""
Draft generation pipeline.

generate_draft(project_id, section_type):
  1. Load project -> solicitation
  2. Build RAG context
  3. Select prompt template
  4. Call Claude API (streaming for long output)
  5. Persist to drafts table
  6. Return draft dict
"""
import anthropic
from backend.config import ANTHROPIC_API_KEY
from backend.db.crud import (
    get_project_by_id,
    get_solicitation_by_id,
    insert_draft,
    get_drafts_for_project,
)
from backend.rag.context_builder import build_context
from backend.rag.prompts import SECTION_PROMPTS, DRAFT_SYSTEM, build_settings_block

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

VALID_SECTION_TYPES = set(SECTION_PROMPTS.keys())


def generate_draft(project_id: int, section_type: str, tone: str = "technical", focus_area: str = "balanced") -> dict:
    """
    Generate a draft section for a project and persist it.
    Returns the inserted draft dict.
    Raises ValueError for bad inputs, RuntimeError on API failure.
    """
    if section_type not in VALID_SECTION_TYPES:
        raise ValueError(
            f"Invalid section_type '{section_type}'. "
            f"Valid types: {sorted(VALID_SECTION_TYPES)}"
        )

    project = get_project_by_id(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    sol = get_solicitation_by_id(project["solicitation_id"])
    if not sol:
        raise ValueError(f"Solicitation {project['solicitation_id']} not found for project {project_id}")

    # Build RAG context
    ctx = build_context(sol["id"])

    # Identify best-matching capability name for prompt placeholder
    top_cap = ctx["scores"][0]["capability"] if ctx["scores"] else "our core capabilities"

    # Render prompt
    prompt_template = SECTION_PROMPTS[section_type]
    user_prompt = prompt_template.format(
        context=ctx["context_text"],
        top_capability=top_cap,
    ) + build_settings_block(tone, focus_area)

    # Call Claude
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=DRAFT_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        content = response.content[0].text.strip()
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API error: {e}") from e

    # Persist
    draft_id = insert_draft(
        project_id=project_id,
        section_type=section_type,
        content=content,
        model_version=MODEL,
    )

    # Return the full draft record
    drafts = get_drafts_for_project(project_id)
    for d in drafts:
        if d["id"] == draft_id:
            return d

    # Fallback (shouldn't happen)
    return {"id": draft_id, "project_id": project_id, "section_type": section_type, "content": content}
