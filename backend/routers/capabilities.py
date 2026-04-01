from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from backend.db.crud import get_all_capabilities, insert_capability, get_scores_for_solicitation, get_solicitation_by_id
from backend.capabilities.aligner import run_alignment

import json

router = APIRouter(tags=["capabilities"])

_align_status: dict = {"running": False, "last_stats": None, "last_error": None}


# ---------------------------------------------------------------------------
# Capabilities CRUD
# ---------------------------------------------------------------------------

@router.get("/capabilities")
def list_capabilities():
    caps = get_all_capabilities()
    # Parse keywords_json for cleaner response
    for c in caps:
        c["keywords"] = json.loads(c.get("keywords_json") or "[]")
    return caps


class CapabilityCreate(BaseModel):
    name: str
    description: str
    keywords: list[str] = []


@router.post("/capabilities", status_code=201)
def create_capability(body: CapabilityCreate):
    insert_capability(body.name, body.description, json.dumps(body.keywords))
    return {"message": f"Capability '{body.name}' created"}


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

@router.get("/align/status")
def align_status():
    return _align_status


@router.post("/align/run")
def trigger_alignment(background_tasks: BackgroundTasks, force_api: bool = False):
    if _align_status["running"]:
        raise HTTPException(status_code=409, detail="Alignment already in progress")
    background_tasks.add_task(_run_alignment_task, force_api)
    return {"message": "Alignment started", "force_api": force_api}


async def _run_alignment_task(force_api: bool) -> None:
    _align_status["running"] = True
    _align_status["last_error"] = None
    try:
        stats = run_alignment(force_api=force_api)
        _align_status["last_stats"] = stats
    except Exception as e:
        _align_status["last_error"] = str(e)
    finally:
        _align_status["running"] = False


# ---------------------------------------------------------------------------
# Per-solicitation alignment scores
# ---------------------------------------------------------------------------

@router.get("/solicitations/{solicitation_id}/alignment")
def get_alignment(solicitation_id: int):
    sol = get_solicitation_by_id(solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    scores = get_scores_for_solicitation(solicitation_id)
    return {
        "solicitation_id": solicitation_id,
        "title": sol["title"],
        "scores": scores,
    }
