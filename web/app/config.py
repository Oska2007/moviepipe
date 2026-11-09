import os
from pathlib import Path

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://moviepipe:moviepipe@db:5432/moviepipe")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_API_URL = os.getenv("TELEGRAM_BOT_API_URL", "http://telegram-bot-api:8081")
    TELEGRAM_BACKUP_CHAT_ID = os.getenv("TELEGRAM_BACKUP_CHAT_ID", "")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

settings = Settings()