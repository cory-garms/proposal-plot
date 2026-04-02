from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.db.crud import (
    get_all_keywords,
    upsert_keyword,
    set_keyword_active,
    delete_keyword,
)
from backend.database import get_connection

router = APIRouter(prefix="/keywords", tags=["keywords"])


class KeywordCreate(BaseModel):
    keyword: str
    source: str = "manual"


def _get_keyword_by_id(keyword_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM search_keywords WHERE id = ?", (keyword_id,)
        ).fetchone()
    return dict(row) if row else None


@router.get("")
def list_keywords(active_only: bool = Query(False)):
    return get_all_keywords(active_only=active_only)


@router.post("", status_code=201)
def create_keyword(body: KeywordCreate):
    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(status_code=422, detail="keyword cannot be empty")
    upsert_keyword(kw, source=body.source)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM search_keywords WHERE keyword = ?", (kw,)
        ).fetchone()
    return dict(row)


@router.patch("/{keyword_id}")
def toggle_keyword(keyword_id: int, active: bool = Query(...)):
    kw = _get_keyword_by_id(keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    set_keyword_active(keyword_id, active)
    return _get_keyword_by_id(keyword_id)


@router.delete("/{keyword_id}", status_code=204)
def remove_keyword(keyword_id: int):
    kw = _get_keyword_by_id(keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    delete_keyword(keyword_id)
