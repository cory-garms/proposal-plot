"""
Capability generation endpoints.

POST /capabilities/generate/url   — generate from ORCID or any URL
POST /capabilities/generate/file  — generate from uploaded PDF or DOCX

Both return a list of suggested capabilities for the frontend to review.
Nothing is saved to the DB until the user confirms via POST /capabilities.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.routers.auth import require_user
from backend.rag.extractor import extract_from_url, extract_from_pdf, extract_from_docx
from backend.rag.capability_generator import generate_capabilities_from_text

router = APIRouter(prefix="/capabilities/generate", tags=["capabilities"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class UrlRequest(BaseModel):
    url: str


@router.post("/url")
def generate_from_url(body: UrlRequest, _: dict = Depends(require_user)):
    """Extract profile text from a URL or ORCID ID and generate capability suggestions."""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    try:
        text = extract_from_url(url)
        capabilities = generate_capabilities_from_text(text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"source": url, "capabilities": capabilities}


@router.post("/file")
async def generate_from_file(
    file: UploadFile = File(...),
    _: dict = Depends(require_user),
):
    """Extract profile text from an uploaded PDF or DOCX and generate capability suggestions."""
    filename = file.filename or ""
    content_type = file.content_type or ""

    is_pdf = filename.lower().endswith(".pdf") or "pdf" in content_type
    is_docx = filename.lower().endswith(".docx") or "wordprocessingml" in content_type

    if not is_pdf and not is_docx:
        raise HTTPException(status_code=422, detail="Only PDF and DOCX files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        if is_pdf:
            text = extract_from_pdf(file_bytes)
        else:
            text = extract_from_docx(file_bytes)
        capabilities = generate_capabilities_from_text(text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"source": filename, "capabilities": capabilities}
