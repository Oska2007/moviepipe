import os
from pathlib import Path

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://moviepipe:moviepipe@db:5432/moviepipe")
    ARIA2_RPC = os.getenv("ARIA2_RPC", "http://aria2:6800/jsonrpc")
    ARIA2_SECRET = os.getenv("ARIA2_SECRET", "")
    DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_API_URL = os.getenv("TELEGRAM_BOT_API_URL", "http://telegram-bot-api:8081")
    TELEGRAM_BACKUP_CHAT_ID = os.getenv("TELEGRAM_BACKUP_CHAT_ID", "")
    R2_ENDPOINT = os.getenv("R2_ENDPOINT", "")
    R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")
    R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")
    R2_BUCKET = os.getenv("R2_BUCKET", "movies")
    R2_PUBLIC_BASE = os.getenv("R2_PUBLIC_BASE", "").rstrip("/")
    POLL = int(os.getenv("WORKER_POLL_SECONDS", "3"))

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "downloads").mkdir(exist_ok=True)
(settings.DATA_DIR / "out").mkdir(exist_ok=True)