import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from backend.db.crud import get_all_solicitations, get_solicitation_by_id
from backend.scraper.sbir_scraper import run as scrape_run
from backend.scraper.run_scrape import build_db_record
from backend.db.crud import upsert_solicitation

router = APIRouter(prefix="/solicitations", tags=["solicitations"])


class ScrapeRequest(BaseModel):
    max_pages: int = 3
    enrich: bool = True
    max_detail: int = 50


# Shared scrape state so the UI can poll if needed
_scrape_status: dict = {"running": False, "last_count": 0, "last_error": None}


@router.get("")
def list_solicitations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    agency: Optional[str] = Query(None),
):
    return get_all_solicitations(limit=limit, offset=offset, agency=agency)


@router.get("/scrape/status")
def scrape_status():
    return _scrape_status


@router.get("/{solicitation_id}")
def get_solicitation(solicitation_id: int):
    row = get_solicitation_by_id(solicitation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return row


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
