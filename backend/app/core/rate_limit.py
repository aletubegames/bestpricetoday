"""
rate_limit.py — Rate limiting via Redis (sliding window).

Fallback para in-memory se Redis não estiver disponível,
garantindo que a app nunca quebre por ausência do Redis.

Uso:
    from app.core.rate_limit import check_rate_limit, get_client_ip

    ip = get_client_ip(request)
    allowed = await check_rate_limit(ip=ip, key="links_create", max_calls=20, window_seconds=60)
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded")
"""
from __future__ import annotations
import time
from collections import defaultdict
from fastapi import Request
from app.core.logging import logger

# Fallback in-memory (usado quando Redis falha)
_fallback: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """
    Retorna o IP real do cliente respeitando proxies reversos (proxy reverso).
    Ordem de preferência:
      1. CF-Connecting-IP (Cloudflare)
      2. X-Forwarded-For (primeiro da lista = cliente original)
      3. X-Real-IP
      4. request.client.host (fallback direto)
    """
    # Cloudflare
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()

    # X-Forwarded-For: pode ser "ip1, ip2, ip3" — pegar o primeiro
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()

    # X-Real-IP
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()

    # Fallback
    return request.client.host if request.client else "unknown"


async def check_rate_limit(
    ip: str,
    key: str,
    max_calls: int = 20,
    window_seconds: int = 60,
) -> bool:
    """
    Sliding window rate limiter.
    Retorna True se a chamada está dentro do limite, False se excedeu.
    Tenta Redis primeiro, cai para in-memory se Redis falhar.
    """
    redis_key = f"rl:{key}:{ip}"
    try:
        from app.core.cache import get_redis
        r = await get_redis()
        now = time.time()
        window_start = now - window_seconds

        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window_seconds + 1)
        results = await pipe.execute()
        count = results[2]
        return count <= max_calls

    except Exception as e:
        logger.warning(f"Redis rate limit fallback (in-memory): {e}")
        now = time.time()
        fb_key = f"{key}:{ip}"
        _fallback[fb_key] = [t for t in _fallback[fb_key] if now - t < window_seconds]
        if len(_fallback[fb_key]) >= max_calls:
            return False
        _fallback[fb_key].append(now)
        return True
