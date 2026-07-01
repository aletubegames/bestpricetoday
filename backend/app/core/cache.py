import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger
import json
import hashlib
from typing import Optional, Any

redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


def make_cache_key(prefix: str, **kwargs) -> str:
    raw = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
    return hashlib.md5(raw.encode()).hexdigest()


async def get_cached(key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        val = await r.get(key)
    except Exception as exc:
        logger.warning(f"Redis unavailable for cache read: {exc}")
        return None

    if val:
        return json.loads(val)
    return None


async def set_cached(key: str, value: Any, ttl: int = None) -> None:
    try:
        r = await get_redis()
        ttl = ttl or settings.CACHE_TTL
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning(f"Redis unavailable for cache write: {exc}")


async def invalidate(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception as exc:
        logger.warning(f"Redis unavailable for cache invalidation: {exc}")
