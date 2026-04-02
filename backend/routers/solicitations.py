import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from backend.db.crud import get_all_solicitations, get_solicitation_by_id, upsert_solicitation, set_solicitation_watched
from backend.scraper.sbir_scraper import run as scrape_run
from backend.scraper.run_scrape import build_db_record

router = APIRouter(prefix="/solicitations", tags=["solicitations"])


class ScrapeRequest(BaseModel):
    max_pages: int = 3
    enrich: bool = True
    max_detail: int = 50


class GrantsScrapeRequest(BaseModel):
    max_results: int = 200


class SamScrapeRequest(BaseModel):
    max_results: int = 200


# Shared scrape state so the UI can poll if needed
_scrape_status: dict = {"running": False, "last_count": 0, "last_error": None}
_grants_status: dict = {"running": False, "last_stats": None, "last_error": None}
_sam_status: dict = {"running": False, "last_stats": None, "last_error": None}


@router.get("")
def list_solicitations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    agency: Optional[str] = Query(None),
    exclude_expired: bool = Query(True),
    sort_by: Optional[str] = Query(None),
    sort_desc: bool = Query(False),
    status_filter: Optional[str] = Query(None),
    profile_id: Optional[str] = Query("1"),
    watched_only: bool = Query(False),
):
    return get_all_solicitations(
        limit=limit,
        offset=offset,
        agency=agency,
        exclude_expired=exclude_expired,
        sort_by=sort_by,
        sort_desc=sort_desc,
        status_filter=status_filter,
        profile_id=profile_id,
        watched_only=watched_only,
    )


@router.get("/scrape/status")
def scrape_status():
    return _scrape_status


@router.get("/{solicitation_id}")
def get_solicitation(solicitation_id: int):
    row = get_solicitation_by_id(solicitation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return row


@router.patch("/{solicitation_id}/watch")
def watch_solicitation(solicitation_id: int, watched: bool = True):
    row = get_solicitation_by_id(solicitation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    set_solicitation_watched(solicitation_id, watched)
    return {"id": solicitation_id, "watched": watched}


@router.post("/scrape")
def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    if _scrape_status["running"]:
        raise HTTPException(status_code=409, detail="Scrape already in progress")
    background_tasks.add_task(_run_scrape, req)
    return {"message": "Scrape started", "params": req.model_dump()}


async def _run_scrape(req: ScrapeRequest) -> None:
    _scrape_status["running"] = True
    _scrape_status["last_error"] = None
    try:
        records = await scrape_run(
            max_pages=req.max_pages,
            enrich=req.enrich,
            max_detail=req.max_detail,
        )
        count = 0
        for record in records:
            db_rec = build_db_record(record)
            if db_rec["title"] and db_rec["url"]:
                upsert_solicitation(db_rec)
                count += 1
        _scrape_status["last_count"] = count
    except Exception as e:
        _scrape_status["last_error"] = str(e)
    finally:
        _scrape_status["running"] = False


@router.post("/scrape/grants")
def trigger_grants_scrape(req: GrantsScrapeRequest, background_tasks: BackgroundTasks):
    if _grants_status["running"]:
        raise HTTPException(status_code=409, detail="Grants scrape already in progress")
    background_tasks.add_task(_run_grants_scrape, req.max_results)
    return {"message": "Grants.gov scrape started", "max_results": req.max_results}


@router.get("/scrape/grants/status")
def grants_scrape_status():
    return _grants_status


@router.post("/scrape/sam")
def trigger_sam_scrape(req: SamScrapeRequest, background_tasks: BackgroundTasks):
    if _sam_status["running"]:
        raise HTTPException(status_code=409, detail="SAM scrape already in progress")
    background_tasks.add_task(_run_sam_scrape, req.max_results)
    return {"message": "SAM.gov scrape started", "max_results": req.max_results}


@router.get("/scrape/sam/status")
def sam_scrape_status():
    return _sam_status


async def _run_sam_scrape(max_results: int) -> None:
    from backend.scraper.sam_scraper import run_sam_scrape
    _sam_status["running"] = True
    _sam_status["last_error"] = None
    try:
        stats = run_sam_scrape(max_results=max_results)
        _sam_status["last_stats"] = stats
    except Exception as e:
        _sam_status["last_error"] = str(e)
    finally:
        _sam_status["running"] = False


async def _run_grants_scrape(max_results: int) -> None:
    from backend.scraper.grants_scraper import run_grants_scrape
    _grants_status["running"] = True
    _grants_status["last_error"] = None
    try:
        stats = run_grants_scrape(max_results=max_results)
        _grants_status["last_stats"] = stats
    except Exception as e:
        _grants_status["last_error"] = str(e)
    finally:
        _grants_status["running"] = False
