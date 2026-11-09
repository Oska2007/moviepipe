import asyncio, sys, traceback
from pathlib import Path
from . import db
from .config import settings
from .downloader import download
from .encoder import encode
from .uploader_r2 import upload
from .uploader_tg import send_video

async def _progress(job_id, pct, stage=None, message=None):
    kw = {"progress": pct}
    if stage:   kw["stage"] = stage
    if message: kw["message"] = message
    await db.set_state(job_id, **kw)

async def process(job):
    jid = job["id"]
    subs = {k: v for k, v in (("sin", job["sub_sinhala"]), ("eng", job["sub_english"])) if v}

    # 1. Download
    await db.set_state(jid, stage="downloading", message="downloading")
    video = await download(job, lambda p: _progress(jid, p, "downloading", f"download {p}%"))

    # 2. Encode
    await db.set_state(jid, status="encoding", stage="encoding", progress=0, message="encoding")
    cfg = await db.get_settings()
    out = await encode(job, video, subs, cfg.get("encode_crf","22"),
                       cfg.get("encode_preset","medium"),
                       cfg.get("audio_mode","aac_stereo"),
                       lambda p: _progress(jid, p, "encoding", f"encode {p}%"))

    # 3. R2
    await db.set_state(jid, status="uploading", stage="r2", progress=0, message="uploading to R2")
    key = f"movies/{jid}/{out.name}"
    key, url, size = await upload(out, key)
    await db.set_state(jid, output_key=key, output_url=url, output_size=size, progress=60)

    # 4. Telegram
    await db.set_state(jid, stage="telegram", message="uploading to Telegram")
    caption = (cfg.get("tg_caption_template","{title}")
               .replace("{title}", job["title"] or out.name)
               .replace("{id}", str(jid)))
    try:
        file_id = await send_video(out, caption)
        await db.set_state(jid, tg_file_id=file_id, progress=95)
    except Exception as e:
        await db.append_log(jid, f"\n[TG error] {e}\n")

    # Done
    await db.set_state(jid, status="done", progress=100, stage="done",
                       message="done", finished_at="now()" if False else None) if False else None
    await db.pool.execute(
        "UPDATE jobs SET status='done', progress=100, stage='done', message='done', "
        "finished_at=now(), updated_at=now() WHERE id=$1", jid)

    # cleanup
    import shutil
    shutil.rmtree(settings.DATA_DIR / "downloads" / str(jid), ignore_errors=True)

async def fail(job, exc):
    tb = traceback.format_exc()[-3000:]
    await db.pool.execute(
        "UPDATE jobs SET status='failed', error=$1, finished_at=now(), updated_at=now(), "
        "log=COALESCE(log,'')||$2 WHERE id=$3", str(exc), tb, job["id"])

async def loop():
    await db.init()
    print("worker ready", flush=True)
    while True:
        try:
            job = await db.claim_job()
        except Exception as e:
            print("db error", e, flush=True)
            await asyncio.sleep(5); continue
        if not job:
            await asyncio.sleep(settings.POLL); continue
        print(f"processing job {job['id']}", flush=True)
        try:
            await process(job)
            print(f"job {job['id']} done", flush=True)
        except Exception as e:
            await fail(job, e)
            print(f"job {job['id']} failed: {e}", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        sys.exit(0)