from pathlib import Path
from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from .db import pool
from .config import settings
from .auth import make_cookie, check_cookie, require_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def logged_in(request: Request) -> bool:
    return check_cookie(request.cookies.get("mp_session"))

# ---------- pages ----------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != settings.ADMIN_USER or password != settings.ADMIN_PASSWORD:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, status_code=401)
    r = RedirectResponse("/", status_code=302)
    r.set_cookie("mp_session", make_cookie(), httponly=True, samesite="lax", max_age=60*60*24*14)
    return r

@router.get("/logout")
async def logout():
    r = RedirectResponse("/login", status_code=302)
    r.delete_cookie("mp_session")
    return r

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: int):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("job.html", {"request": request, "job_id": job_id})

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request})

# ---------- api ----------
@router.get("/api/jobs")
async def api_jobs(request: Request, _=Depends(require_login)):
    rows = await pool().fetch("SELECT * FROM jobs ORDER BY id DESC LIMIT 200")
    return [dict(r) for r in rows]

@router.get("/api/jobs/{job_id}")
async def api_job(job_id: int, request: Request, _=Depends(require_login)):
    r = await pool().fetchrow("SELECT * FROM jobs WHERE id=$1", job_id)
    if not r:
        raise HTTPException(404)
    return dict(r)

@router.post("/api/jobs")
async def api_new_job(request: Request, _=Depends(require_login)):
    body = await request.json()
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "url required")
    title = (body.get("title") or "").strip() or None
    row = await pool().fetchrow(
        "INSERT INTO jobs(source_url,title) VALUES($1,$2) RETURNING *", url, title)
    return dict(row)

@router.post("/api/jobs/{job_id}/retry")
async def api_retry(job_id: int, request: Request, _=Depends(require_login)):
    await pool().execute(
        "UPDATE jobs SET status='queued', progress=0, error=NULL, finished_at=NULL WHERE id=$1", job_id)
    return {"ok": True}

@router.post("/api/jobs/{job_id}/cancel")
async def api_cancel(job_id: int, request: Request, _=Depends(require_login)):
    await pool().execute("UPDATE jobs SET status='cancelled' WHERE id=$1 AND status NOT IN ('done','failed')", job_id)
    return {"ok": True}

@router.get("/api/settings")
async def api_settings(request: Request, _=Depends(require_login)):
    rows = await pool().fetch("SELECT key,value FROM settings")
    return {r["key"]: r["value"] for r in rows}

@router.post("/api/settings")
async def api_save_settings(request: Request, _=Depends(require_login)):
    body = await request.json()
    async with pool().acquire() as c:
        async with c.transaction():
            for k, v in body.items():
                await c.execute(
                    "INSERT INTO settings(key,value) VALUES($1,$2) "
                    "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value",
                    k, str(v))
    return {"ok": True}

@router.post("/api/jobs/{job_id}/subs")
async def api_upload_subs(job_id: int, request: Request, lang: str, file: UploadFile = File(...), _=Depends(require_login)):
    if lang not in ("sin", "eng"):
        raise HTTPException(400, "lang must be sin or eng")
    d = settings.DATA_DIR / "subs" / str(job_id)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{lang}.srt"
    p.write_bytes(await file.read())
    col = "sub_sinhala" if lang == "sin" else "sub_english"
    await pool().execute(f"UPDATE jobs SET {col}=$1 WHERE id=$2", str(p), job_id)
    return {"ok": True, "path": str(p)}