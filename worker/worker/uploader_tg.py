from pathlib import Path
import httpx
from .config import settings

async def send_video(path: Path, caption: str) -> str:
    if not settings.TELEGRAM_BACKUP_CHAT_ID:
        return ""
    url = f"{settings.TELEGRAM_BOT_API_URL}/bot{settings.TELEGRAM_BOT_TOKEN}/sendVideo"
    timeout = httpx.Timeout(connect=30, read=None, write=None, pool=None)
    async with httpx.AsyncClient(timeout=timeout) as c:
        with open(path, "rb") as f:
            r = await c.post(url, data={
                "chat_id": settings.TELEGRAM_BACKUP_CHAT_ID,
                "caption": caption[:1000],
                "supports_streaming": "true",
            }, files={"video": (path.name, f, "video/mp4")})
        r.raise_for_status()
        j = r.json()
        if not j.get("ok"):
            raise RuntimeError(f"tg: {j}")
        return j["result"]["video"]["file_id"]