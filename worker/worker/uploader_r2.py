import asyncio
from pathlib import Path
import boto3
from .config import settings

def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY,
        aws_secret_access_key=settings.R2_SECRET_KEY,
        region_name="auto",
    )

async def upload(path: Path, key: str) -> tuple[str, str, int]:
    s3 = _client()
    def _do():
        s3.upload_file(str(path), settings.R2_BUCKET, key, ExtraArgs={
            "ContentType": "video/mp4",
            "CacheControl": "public, max-age=31536000, immutable",
        })
    await asyncio.to_thread(_do)
    url = f"{settings.R2_PUBLIC_BASE}/{key}" if settings.R2_PUBLIC_BASE else f"r2://{settings.R2_BUCKET}/{key}"
    return key, url, path.stat().st_size