import asyncpg
from .config import settings

pool: asyncpg.Pool | None = None

async def init():
    global pool
    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=4)

async def claim_job():
    row = await pool.fetchrow("""
        UPDATE jobs SET status='downloading', started_at=now(),
                        attempts=attempts+1, updated_at=now(), progress=0
        WHERE id = (
          SELECT id FROM jobs WHERE status='queued'
          ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1
        )
        RETURNING *;
    """)
    return row

async def set_state(job_id, **kw):
    if not kw:
        return
    cols, vals = [], []
    for i, (k, v) in enumerate(kw.items(), 1):
        cols.append(f"{k}=${i}")
        vals.append(v)
    await pool.execute(
        f"UPDATE jobs SET {', '.join(cols)}, updated_at=now() WHERE id=${len(vals)+1}",
        *vals, job_id)

async def append_log(job_id, text):
    await pool.execute(
        "UPDATE jobs SET log = COALESCE(log,'') || $1 WHERE id=$2",
        text[-4000:], job_id)

async def get_settings():
    rows = await pool.fetch("SELECT key,value FROM settings")
    return {r["key"]: r["value"] for r in rows}