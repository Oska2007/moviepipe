import asyncio, json, subprocess
from pathlib import Path
from .config import settings

async def _probe_duration(path) -> float:
    p = await asyncio.create_subprocess_exec(
        "ffprobe","-v","quiet","-print_format","json",
        "-show_format", str(path),
        stdout=asyncio.subprocess.PIPE)
    out, _ = await p.communicate()
    data = json.loads(out or b"{}")
    return float(data.get("format", {}).get("duration", 0) or 0)

async def encode(job, video: Path, subs: dict, crf: str, preset: str,
                 audio_mode: str, on_progress):
    out_dir = settings.DATA_DIR / "out" / str(job["id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"movie_{job['id']}_x264.mp4"

    cmd = ["ffmpeg","-y","-i", str(video)]
    sub_inputs = []
    idx = 1
    for lang in ("sin","eng"):
        if subs.get(lang):
            cmd += ["-i", subs[lang]]
            sub_inputs.append((idx, lang))
            idx += 1

    cmd += ["-map","0:v:0","-map","0:a:0?"]
    for i,(stream_idx, lang) in enumerate(sub_inputs):
        cmd += ["-map", f"{stream_idx}:0",
                f"-metadata:s:s:{i}", f"language={lang}",
                f"-metadata:s:s:{i}", f"title={lang.capitalize()}"]

    cmd += ["-c:v","libx264","-crf",str(crf),"-preset",preset,
            "-pix_fmt","yuv420p"]
    if audio_mode == "aac_stereo":
        cmd += ["-c:a","aac","-b:a","192k","-ac","2"]
    else:
        cmd += ["-c:a","copy"]
    if sub_inputs:
        cmd += ["-c:s","mov_text"]
    cmd += ["-movflags","+faststart","-progress","pipe:1","-nostats", str(out)]

    duration = await _probe_duration(video) or 1
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        s = line.decode(errors="ignore").strip()
        if s.startswith("out_time_ms="):
            try:
                us = int(s.split("=")[1])
                pct = min(99, int(us / 1_000_000 / duration * 100))
                await on_progress(pct)
            except Exception:
                pass
    if await proc.wait() != 0:
        err = (await proc.stderr.read()).decode(errors="ignore")[-1500:]
        raise RuntimeError(f"ffmpeg failed: {err}")
    await on_progress(100)
    return out