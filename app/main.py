import asyncio
import shutil
from contextlib import asynccontextmanager
from typing import Literal

import psutil
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.models import Job
from app.queue import job_queue
from app.security import create_session_token, require_auth, verify_password
from app.downloader.torrent import get_torrent_files

class LoginRequest(BaseModel):
    username: str
    password: str

class JobCreateRequest(BaseModel):
    source_type: Literal["url", "magnet", "torrent", "upload"]
    source: str = Field(min_length=1, max_length=4096)
    priority: int = 100
    torrent_file_index: int | None = None
    custom_output_name: str | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    job_queue.start()
    yield

app = FastAPI(title="Standalone Media Processing Engine", version="0.1.0", lifespan=lifespan)

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    if payload.username != settings.admin_username or not verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_session_token(payload.username), "token_type": "bearer"}

@app.post("/api/torrent/inspect", dependencies=[Depends(require_auth)])
async def inspect_torrent(payload: JobCreateRequest):
    if payload.source_type not in ["magnet", "torrent"]:
        raise HTTPException(status_code=400, detail="Only magnet or torrent files supported")
    try:
        loop = asyncio.get_running_loop()
        files = await loop.run_in_executor(None, get_torrent_files, payload.source)
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/jobs", dependencies=[Depends(require_auth)])
async def create_job(payload: JobCreateRequest, db: Session = Depends(get_db)):
    job = Job(
        status="PENDING",
        source_type=payload.source_type,
        source=payload.source,
        torrent_file_index=payload.torrent_file_index,
        custom_output_name=payload.custom_output_name
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    await job_queue.enqueue(job.id, priority=payload.priority)
    return {"job_id": job.id, "status": job.status}

@app.get("/api/jobs", dependencies=[Depends(require_auth)])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(200)).all()
    return [
        {
            "id": j.id,
            "status": j.status,
            "source_type": j.source_type,
            "source": j.source,
            "custom_output_name": j.custom_output_name,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "error_message": j.error_message,
        }
        for j in jobs
    ]

@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_auth)])
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/jobs/{job_id}/retry", dependencies=[Depends(require_auth)])
async def retry_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in {"FAILED", "NEEDS_REVIEW", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Job is not retryable")

    job.status = "PENDING"
    job.error_message = None
    job.retry_count += 1
    db.commit()
    await job_queue.enqueue(job.id)
    return {"job_id": job.id, "status": job.status}

@app.post("/api/jobs/{job_id}/cancel", dependencies=[Depends(require_auth)])
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    job.status = "CANCELLED"
    db.commit()
    return {"job_id": job.id, "status": job.status}

@app.get("/api/system/health")
def health():
    return {"status": "ok", "env": settings.app_env}

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard/")

app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")