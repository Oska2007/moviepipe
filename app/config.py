from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "production"
    app_secret: str = "CHANGE_ME"
    app_domain: str = "localhost"

    admin_username: str = "admin"
    admin_password_hash: str = "CHANGE_ME"
    admin_api_key: str = "CHANGE_ME"

    database_url: str = "sqlite:///./data/media.db"

    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_endpoint: str = ""
    r2_public_base_url: str = ""

    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    ai_provider: str = "local"
    ai_api_key: str = ""
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"

    max_concurrent_jobs: int = 1
    max_cpu_threads: int = 2
    max_temp_storage_gb: int = 30
    min_free_disk_gb: int = 8

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()