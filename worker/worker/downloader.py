import asyncio, json, subprocess, shutil
from pathlib import Path
import httpx
from .config import settings

async def _rpc(client, method, params):
    r = await client.post(settings.ARIA2_RPC, json={
        "jsonrpc":"2.0","id":"x","method":method,
        "params": [f"token:{settings.ARIA2_SECRET}", *params]})
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"aria2: {j['error']}")
    return j["result"]

async def download(job, on_progress):
    out_dir = settings.DATA_DIR / "downloads" / str(job["id"])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    url = job["source_url"]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, read=30)) as c:
            gid = await _rpc(c, "aria2.addUri", [[url], {"dir": str(out_dir)}])
            while True:
                await asyncio.sleep(2)
                st = await _rpc(c, "aria2.tellStatus", [gid, ["status","completedLength","totalLength"]])
                if st["status"] == "complete":
                    break
                if st["status"] in ("error","removed"):
                    raise RuntimeError(f"aria2 status {st['status']}")
                total = int(st["totalLength"] or 0)
                done = int(st["completedLength"] or 0)
                if total > 0:
                    await on_progress(int(done*100/total))
    except Exception:
        await _ytdlp(url, out_dir, on_progress)

    return _largest_video(out_dir)

async def _ytdlp(url, out_dir, on_progress):
    cmd = ["yt-dlp","-N","4","-o", str(out_dir / "%(title)s.%(ext)s"), url]
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    async for line in proc.stderr:
        s = line.decode(errors="ignore").strip()
        if "%" in s and "of" in s:
            try:
                pct = int(s.split("%")[0].split()[-1])
                await on_progress(pct)
            except Exception:
                pass
    if await proc.wait() != 0:
        raise RuntimeError("yt-dlp failed and aria2 failed")

def _largest_video(folder: Path) -> Path:
    vids = [p for p in folder.rglob("*")
            if p.suffix.lower() in (".mp4",".mkv",".avi",".mov",".webm",".ts",".m4v")]
    if not vids:
        raise RuntimeError("No video file found in download")
    return max(vids, key=lambda p: p.stat().st_size)