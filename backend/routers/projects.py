import difflib

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from backend.routers.auth import require_user

from backend.db.crud import (
    insert_project,
    get_project_by_id,
    get_solicitation_by_id,
    get_drafts_for_project,
    get_draft_by_id,
    update_draft_content,
    get_scores_for_solicitation,
)
from backend.export.docx_writer import build_docx
from backend.export.pdf_writer import build_pdf
from backend.rag.generator import generate_draft, VALID_SECTION_TYPES

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    solicitation_id: int
    title: str


VALID_TONES = {"technical", "executive", "persuasive"}
VALID_FOCUS_AREAS = {"balanced", "innovation", "feasibility", "commercialization"}


class GenerateRequest(BaseModel):
    section_type: str = "technical_volume"
    tone: str = "technical"
    focus_area: str = "balanced"


@router.post("", status_code=201)
def create_project(body: ProjectCreate, _user: dict = Depends(require_user)):
    sol = get_solicitation_by_id(body.solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    project_id = insert_project(body.solicitation_id, body.title)
    project = get_project_by_id(project_id)
    scores = get_scores_for_solicitation(body.solicitation_id)
    return {**project, "alignment_scores": scores}


@router.get("/{project_id}")
def get_project(project_id: int):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    scores = get_scores_for_solicitation(project["solicitation_id"])
    return {**project, "alignment_scores": scores}


@router.post("/{project_id}/generate")
def generate(project_id: int, body: GenerateRequest, _user: dict = Depends(require_user)):
    if body.section_type not in VALID_SECTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid section_type. Valid: {sorted(VALID_SECTION_TYPES)}",
        )
    if body.tone not in VALID_TONES:
        raise HTTPException(status_code=422, detail=f"Invalid tone. Valid: {sorted(VALID_TONES)}")
    if body.focus_area not in VALID_FOCUS_AREAS:
        raise HTTPException(status_code=422, detail=f"Invalid focus_area. Valid: {sorted(VALID_FOCUS_AREAS)}")
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        draft = generate_draft(project_id, body.section_type, tone=body.tone, focus_area=body.focus_area)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return draft


@router.get("/{project_id}/drafts")
def list_drafts(project_id: int):
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_drafts_for_project(project_id)


class DraftUpdate(BaseModel):
    content: str


@router.get("/{project_id}/drafts/{draft_id}/export/docx")
def export_draft_docx(project_id: int, draft_id: int):
    draft = get_draft_by_id(draft_id)
    if not draft or draft["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    project = get_project_by_id(project_id)
    sol = get_solicitation_by_id(project["solicitation_id"])
    filename = f"draft_{draft_id}_{draft['section_type']}.docx"
    data = build_docx(
        title=sol.get("title", project["title"]),
        agency=sol.get("agency", ""),
        content=draft["content"],
    )
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/drafts/{draft_id}/export/pdf")
def export_draft_pdf(project_id: int, draft_id: int):
    draft = get_draft_by_id(draft_id)
    if not draft or draft["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    project = get_project_by_id(project_id)
    sol = get_solicitation_by_id(project["solicitation_id"])
    filename = f"draft_{draft_id}_{draft['section_type']}.pdf"
    data = build_pdf(
        title=sol.get("title", project["title"]),
        agency=sol.get("agency", ""),
        content=draft["content"],
    )
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/drafts/{draft_id}/diff")
def diff_drafts(project_id: int, draft_id: int, against: int = Query(..., description="ID of the draft to compare against")):
    draft_b = get_draft_by_id(draft_id)
    draft_a = get_draft_by_id(against)
    if not draft_b or draft_b["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not draft_a or draft_a["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Comparison draft not found")
    a_lines = draft_a["content"].splitlines(keepends=True)
    b_lines = draft_b["content"].splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        a_lines, b_lines,
        fromfile=f"draft {against} ({draft_a['generated_at'][:16]})",
        tofile=f"draft {draft_id} ({draft_b['generated_at'][:16]})",
        lineterm="",
    ))
    return {"diff": diff_lines}


@router.patch("/{project_id}/drafts/{draft_id}")
def update_draft(project_id: int, draft_id: int, body: DraftUpdate, _user: dict = Depends(require_user)):
    draft = get_draft_by_id(draft_id)
    if not draft or draft["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    if not body.content.strip():
        raise HTTPException(status_code=422, detail="Content cannot be empty")
    update_draft_content(draft_id, body.content)
    return get_draft_by_id(draft_id)
