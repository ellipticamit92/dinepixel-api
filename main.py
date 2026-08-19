"""
FastAPI wrapper around extract_menu(). Exposes menu extraction as an async
job over HTTP: upload a file, poll for status, read back the extracted Menu.

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from categorize import categorize_items_stream
from extract import extract_menu
from schemas import CategorizeItemIn, CategorizeRequest, Menu

load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY not set. Add API_KEY=<a secret> to .env")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

app = FastAPI(
    title="MenuLens API",
    description="Extract structured menu data from a menu photo or PDF using Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "done", "error"]
    created_at: datetime
    menu: Optional[Menu] = None
    error: Optional[str] = None


JOBS: dict[str, JobStatus] = {}


def run_extraction(job_id: str, file_path: Path) -> None:
    JOBS[job_id].status = "processing"
    try:
        JOBS[job_id].menu = extract_menu(file_path)
        JOBS[job_id].status = "done"
    except Exception as e:
        JOBS[job_id].error = str(e)
        JOBS[job_id].status = "error"
    finally:
        file_path.unlink(missing_ok=True)
        file_path.parent.rmdir()


@app.post("/extract", response_model=JobStatus, dependencies=[Depends(require_api_key)])
async def create_extraction_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> JobStatus:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or 'unknown'}")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 15MB)")

    job_id = str(uuid.uuid4())
    tmp_dir = Path(tempfile.mkdtemp(prefix="menulens_"))
    tmp_path = tmp_dir / f"upload{suffix}"
    tmp_path.write_bytes(contents)

    JOBS[job_id] = JobStatus(job_id=job_id, status="pending", created_at=datetime.now(timezone.utc))
    background_tasks.add_task(run_extraction, job_id, tmp_path)
    return JOBS[job_id]


@app.get("/extract/{job_id}", response_model=JobStatus, dependencies=[Depends(require_api_key)])
async def get_extraction_job(job_id: str) -> JobStatus:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def sse_categorize(items: list[CategorizeItemIn]) -> Iterator[str]:
    try:
        for categorized in categorize_items_stream(items):
            yield f"data: {categorized.model_dump_json()}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return
    yield "event: done\ndata: {}\n\n"


@app.post("/categorize", dependencies=[Depends(require_api_key)])
async def categorize_menu(request: CategorizeRequest) -> StreamingResponse:
    if not request.items:
        raise HTTPException(status_code=400, detail="items must not be empty")
    return StreamingResponse(
        sse_categorize(request.items),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health() -> dict:
    poppler_ok = shutil.which("pdftoppm") is not None
    return {
        "status": "ok" if poppler_ok else "degraded",
        "poppler_installed": poppler_ok,
    }
