from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.crud import (
    insert_project,
    get_project_by_id,
    get_solicitation_by_id,
    get_drafts_for_project,
    get_scores_for_solicitation,
)
from backend.rag.generator import generate_draft, VALID_SECTION_TYPES

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    solicitation_id: int
    title: str


class GenerateRequest(BaseModel):
    section_type: str = "technical_volume"


@router.post("", status_code=201)
def create_project(body: ProjectCreate):
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
def generate(project_id: int, body: GenerateRequest):
    if body.section_type not in VALID_SECTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid section_type. Valid: {sorted(VALID_SECTION_TYPES)}",
        )
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        draft = generate_draft(project_id, body.section_type)
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
