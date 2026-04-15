import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from pydantic import BaseModel

from backend.db.crud import get_all_solicitations, get_solicitation_by_id, upsert_solicitation, set_solicitation_watched, get_all_profiles
from backend.scraper.sbir_scraper import run as scrape_run
from backend.scraper.run_scrape import build_db_record
from backend.routers.auth import require_admin

router = APIRouter(prefix="/solicitations", tags=["solicitations"])


class ScrapeRequest(BaseModel):
    max_pages: int = 30
    enrich: bool = True
    max_detail: int = 150


class GrantsScrapeRequest(BaseModel):
    max_results: int = 200


class SamScrapeRequest(BaseModel):
    max_results: int = 200

class SamCsvRequest(BaseModel):
    filename: str = "SAM_ContractOpportunitiesFull.csv"
    max_results: int = 10000


# Shared scrape state so the UI can poll if needed
_scrape_status: dict = {"running": False, "last_count": 0, "last_error": None}
_grants_status: dict = {"running": False, "last_stats": None, "last_error": None}
_sam_status: dict = {"running": False, "last_stats": None, "last_error": None}
_sam_csv_status: dict = {"running": False, "last_stats": None, "last_error": None}
_dod_status: dict = {"running": False, "last_stats": None, "last_error": None}


_shared_profile_id_cache: Optional[str] = None

def _get_shared_profile_id() -> Optional[str]:
    global _shared_profile_id_cache
    if _shared_profile_id_cache is None:
        profiles = get_all_profiles()
        shared = next((p for p in profiles if p.get("shared")), None)
        _shared_profile_id_cache = str(shared["id"]) if shared else None
    return _shared_profile_id_cache


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
    source: Optional[str] = Query(None),
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
        shared_profile_id=_get_shared_profile_id(),
        watched_only=watched_only,
        source=source,
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
def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
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
def trigger_grants_scrape(req: GrantsScrapeRequest, background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
    if _grants_status["running"]:
        raise HTTPException(status_code=409, detail="Grants scrape already in progress")
    background_tasks.add_task(_run_grants_scrape, req.max_results)
    return {"message": "Grants.gov scrape started", "max_results": req.max_results}


@router.get("/scrape/grants/status")
def grants_scrape_status():
    return _grants_status


@router.post("/scrape/sam")
def trigger_sam_scrape(req: SamScrapeRequest, background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
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
        if "error" in stats:
            _sam_status["last_error"] = stats["error"]
        else:
            _sam_status["last_stats"] = stats
    except Exception as e:
        _sam_status["last_error"] = str(e)
    finally:
        _sam_status["running"] = False


@router.post("/scrape/dod")
def trigger_dod_scrape(background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
    if _dod_status["running"]:
        raise HTTPException(status_code=409, detail="DOD scrape already in progress")
    background_tasks.add_task(_run_dod_scrape)
    return {"message": "DOD SBIR/STTR scrape started"}


@router.get("/scrape/dod/status")
def dod_scrape_status():
    return _dod_status


async def _run_dod_scrape() -> None:
    from backend.scraper.dod_scraper import run_sync as dod_sync
    from backend.scraper.run_scrape import build_db_record
    _dod_status["running"] = True
    _dod_status["last_error"] = None
    inserted = errors = 0
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, dod_sync)
        for record in records:
            db_rec = build_db_record(record)
            db_rec["source"] = "dod"
            if not db_rec["title"] or not db_rec["url"]:
                continue
            try:
                upsert_solicitation(db_rec)
                inserted += 1
            except Exception as e:
                print(f"[dod] db error: {e}")
                errors += 1
        _dod_status["last_stats"] = {"persisted": inserted, "errors": errors}
    except Exception as e:
        _dod_status["last_error"] = str(e)
    finally:
        _dod_status["running"] = False


@router.post("/import/sam-csv")
def trigger_sam_csv_import(req: SamCsvRequest, background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
    if _sam_csv_status["running"]:
        raise HTTPException(status_code=409, detail="SAM CSV import already in progress")
    # Only allow plain filenames — no path traversal
    if "/" in req.filename or "\\" in req.filename:
        raise HTTPException(status_code=422, detail="filename must not contain path separators")
    background_tasks.add_task(_run_sam_csv_import, req.filename, req.max_results)
    return {"message": "SAM CSV import started", "filename": req.filename, "max_results": req.max_results}


@router.get("/import/sam-csv/status")
def sam_csv_import_status():
    return _sam_csv_status


async def _run_sam_csv_import(filename: str, max_results: int) -> None:
    import os
    from backend.scraper.sam_csv_parser import run_sam_csv_import
    from backend.capabilities.aligner import run_alignment
    from backend.routers.capabilities import _align_status
    _sam_csv_status["running"] = True
    _sam_csv_status["last_error"] = None
    try:
        # Resolve relative to project root (parent of backend/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        csv_path = os.path.join(project_root, filename)
        # Also check one level up (e.g. when CSV sits next to the repo dir)
        if not os.path.exists(csv_path):
            csv_path = os.path.join(os.path.dirname(project_root), filename)
        stats = run_sam_csv_import(csv_path, max_results=max_results)
        if "error" in stats:
            _sam_csv_status["last_error"] = stats["error"]
        else:
            _sam_csv_status["last_stats"] = stats
            # Auto-score new solicitations against all shared profiles
            if stats.get("inserted", 0) > 0 and not _align_status["running"]:
                print(f"[sam-csv] {stats['inserted']} new records — triggering alignment")
                _align_status["running"] = True
                _align_status["last_error"] = None
                try:
                    align_stats = run_alignment(skip_scored=True, include_expired=False)
                    _align_status["last_stats"] = align_stats
                except Exception as ae:
                    _align_status["last_error"] = str(ae)
                finally:
                    _align_status["running"] = False
    except Exception as e:
        _sam_csv_status["last_error"] = str(e)
    finally:
        _sam_csv_status["running"] = False


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
