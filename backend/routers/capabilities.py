from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from backend.db.crud import (
    get_all_capabilities, insert_capability, update_capability, delete_capability,
    get_scores_for_solicitation, get_solicitation_by_id,
    get_all_profiles, insert_profile,
    get_all_keywords, upsert_keyword, set_keyword_active, delete_keyword,
    get_profile_by_id,
)
from backend.capabilities.aligner import run_alignment
from backend.routers.auth import get_current_user, require_user, require_admin, require_own_profile_or_admin

import json

router = APIRouter(tags=["capabilities"])

_align_status: dict = {"running": False, "last_stats": None, "last_error": None}


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

@router.get("/profiles")
def list_profiles(user: dict | None = Depends(get_current_user)):
    if user and user.get("is_admin"):
        return get_all_profiles(include_all=True)
    user_id = user["id"] if user else None
    return get_all_profiles(user_id=user_id)

class ProfileCreate(BaseModel):
    name: str

@router.post("/profiles", status_code=201)
def create_profile(body: ProfileCreate, user: dict = Depends(require_user)):
    pid = insert_profile(body.name, user_id=user["id"])
    return {"message": f"Profile '{body.name}' created", "id": pid}

# ---------------------------------------------------------------------------
# Capabilities CRUD
# ---------------------------------------------------------------------------

@router.get("/capabilities")
def list_capabilities(profile_id: int | None = None):
    caps = get_all_capabilities(profile_id=profile_id)
    # Parse keywords_json for cleaner response
    for c in caps:
        c["keywords"] = json.loads(c.get("keywords_json") or "[]")
    return caps


class CapabilityCreate(BaseModel):
    name: str
    description: str
    keywords: list[str] = []
    profile_id: int = 1


def _assert_owns_profile(profile_id: int, user: dict) -> None:
    """Raise 403 if the user doesn't own the profile. Admins are always allowed."""
    if user.get("is_admin"):
        return
    profile = get_profile_by_id(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.get("shared") or profile.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="You can only modify capabilities on profiles you own.",
        )


def _assert_owns_capability(capability_id: int, user: dict) -> dict:
    """Fetch the capability and assert the user owns its profile. Returns the capability."""
    if user.get("is_admin"):
        caps = get_all_capabilities()
        cap = next((c for c in caps if c["id"] == capability_id), None)
        if not cap:
            raise HTTPException(status_code=404, detail="Capability not found")
        return cap
    # For non-admins, only fetch from profiles they own (not shared)
    owned_profiles = [p["id"] for p in get_all_profiles(user_id=user["id"]) if not p.get("shared")]
    for pid in owned_profiles:
        caps = get_all_capabilities(profile_id=pid)
        cap = next((c for c in caps if c["id"] == capability_id), None)
        if cap:
            return cap
    raise HTTPException(
        status_code=403,
        detail="You can only modify capabilities on profiles you own.",
    )


def _background_align_profile(profile_id: int) -> None:
    """Run alignment for a single profile in the background. Non-fatal."""
    if _align_status["running"]:
        return
    _align_status["running"] = True
    _align_status["last_error"] = None
    try:
        stats = run_alignment(profile_id=profile_id, skip_scored=True, include_expired=False)
        _align_status["last_stats"] = stats
    except Exception as e:
        _align_status["last_error"] = str(e)
    finally:
        _align_status["running"] = False


@router.post("/capabilities", status_code=201)
def create_capability(body: CapabilityCreate, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    _assert_owns_profile(body.profile_id, user)
    insert_capability(body.name, body.description, json.dumps(body.keywords), body.profile_id)
    for kw in body.keywords:
        if kw.strip():
            upsert_keyword(kw.strip().lower(), source="capability")
    # Auto-score the profile in the background so the dashboard updates without manual intervention
    background_tasks.add_task(_background_align_profile, body.profile_id)
    return {"message": f"Capability '{body.name}' created"}


class CapabilityUpdate(BaseModel):
    name: str
    description: str
    keywords: list[str] = []


@router.patch("/capabilities/{capability_id}")
def edit_capability(capability_id: int, body: CapabilityUpdate, background_tasks: BackgroundTasks, user: dict = Depends(require_user)):
    cap = _assert_owns_capability(capability_id, user)
    update_capability(capability_id, body.name, body.description, json.dumps(body.keywords))
    for kw in body.keywords:
        if kw.strip():
            upsert_keyword(kw.strip().lower(), source="capability")
    background_tasks.add_task(_background_align_profile, cap["profile_id"])
    return {"message": f"Capability '{body.name}' updated"}


@router.delete("/capabilities/{capability_id}", status_code=204)
def remove_capability(capability_id: int, user: dict = Depends(require_user)):
    _assert_owns_capability(capability_id, user)
    delete_capability(capability_id)


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

@router.get("/align/status")
def align_status():
    return _align_status


@router.post("/align/run")
def trigger_alignment(background_tasks: BackgroundTasks, force_api: bool = False, include_expired: bool = False, profile_id: int | None = None, skip_scored: bool = True, _: dict = Depends(require_own_profile_or_admin)):
    if _align_status["running"]:
        raise HTTPException(status_code=409, detail="Alignment already in progress")
    background_tasks.add_task(_run_alignment_task, force_api, include_expired, profile_id, skip_scored)
    return {"message": "Alignment started", "force_api": force_api, "include_expired": include_expired, "profile_id": profile_id, "skip_scored": skip_scored}


async def _run_alignment_task(force_api: bool, include_expired: bool = False, profile_id: int | None = None, skip_scored: bool = True) -> None:
    _align_status["running"] = True
    _align_status["last_error"] = None
    try:
        stats = run_alignment(force_api=force_api, include_expired=include_expired, profile_id=profile_id, skip_scored=skip_scored)
        _align_status["last_stats"] = stats
    except Exception as e:
        _align_status["last_error"] = str(e)
    finally:
        _align_status["running"] = False

@router.post("/solicitations/{solicitation_id}/align")
def trigger_single_alignment(solicitation_id: int):
    # Synchronously run alignment for a single ID to provide immediate feedback
    from backend.capabilities.aligner import run_alignment
    stats = run_alignment(solicitation_ids=[solicitation_id], force_api=True)
    if "error" in stats:
        raise HTTPException(status_code=500, detail=stats["error"])
    return {"message": "Alignment rescored", "stats": stats}


# ---------------------------------------------------------------------------
# Search Keywords
# ---------------------------------------------------------------------------

@router.get("/keywords")
def list_keywords(active_only: bool = False):
    return get_all_keywords(active_only=active_only)


class KeywordCreate(BaseModel):
    keyword: str


@router.post("/keywords", status_code=201)
def create_keyword(body: KeywordCreate):
    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(status_code=422, detail="keyword cannot be empty")
    upsert_keyword(kw, source="manual")
    return {"message": f"Keyword '{kw}' added"}


@router.patch("/keywords/{keyword_id}")
def toggle_keyword(keyword_id: int, active: bool):
    set_keyword_active(keyword_id, active)
    return {"message": "Updated"}


@router.delete("/keywords/{keyword_id}", status_code=204)
def remove_keyword(keyword_id: int):
    delete_keyword(keyword_id)


# ---------------------------------------------------------------------------
# Per-solicitation alignment scores
# ---------------------------------------------------------------------------

@router.get("/solicitations/{solicitation_id}/alignment")
def get_alignment(solicitation_id: int, profile_id: int | None = None):
    sol = get_solicitation_by_id(solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    scores = get_scores_for_solicitation(solicitation_id, profile_id=profile_id)
    return {
        "solicitation_id": solicitation_id,
        "title": sol["title"],
        "scores": scores,
    }
