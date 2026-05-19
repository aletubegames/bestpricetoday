"""
keep_warm.py — Previne cold start do HF Space.

O HF Space grátis dorme após ~15 min de inatividade.
Este worker faz um self-ping a cada 4 minutos para manter o processo vivo.
Custo: ~360 requests/dia internos, praticamente zero de CPU.
"""
import asyncio
import httpx
from app.core.logging import logger

INTERVAL_SECONDS = 4 * 60   # 4 minutos
SELF_URL         = "http://localhost:7860/health"  # porta padrão HF Space (Docker)


async def start_keep_warm():
    """Background task de self-ping."""
    await asyncio.sleep(30)  # aguarda startup completo
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(SELF_URL)
            logger.debug(f"Keep-warm ping: HTTP {r.status_code}")
        except Exception as e:
            logger.debug(f"Keep-warm ping failed (normal during startup): {e}")
        await asyncio.sleep(INTERVAL_SECONDS)
