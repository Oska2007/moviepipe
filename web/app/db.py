import asyncpg
from .config import settings

_pool: asyncpg.Pool | None = None

async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=10)

async def close_pool():
    if _pool:
        await _pool.close()

def pool() -> asyncpg.Pool:
    assert _pool is not None
    return _pool