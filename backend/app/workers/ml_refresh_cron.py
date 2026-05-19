"""
ml_refresh_cron.py — Renova o token do Mercado Livre automaticamente.

Roda como background task na startup do FastAPI.
Loop: a cada 25 minutos verifica se o token está próximo de expirar e renova.
O ml_token_service já tem lógica de refresh; este cron garante que ela
seja chamada periodicamente mesmo sem requests de usuário.
"""
import asyncio
from app.core.logging import logger

INTERVAL_SECONDS = 25 * 60  # 25 minutos


async def run_ml_refresh():
    """Executa uma verificação/refresh do token ML."""
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.ml_token_service import get_token, get_token_status

        async with AsyncSessionLocal() as db:
            status = await get_token_status(db)
            minutes = status.get("expires_in_minutes", 999)

            if status.get("status") in ("expired", "expiring_soon") or minutes < 30:
                logger.info(f"ML token refresh cron: token expira em {minutes}min — renovando")
                token = await get_token(db)  # auto-renova internamente
                if token:
                    logger.info("ML token refresh cron: token renovado com sucesso")
                else:
                    logger.warning("ML token refresh cron: refresh falhou — reauth necessário")
            else:
                logger.debug(f"ML token refresh cron: token OK, expira em {minutes}min")
    except Exception as e:
        logger.error(f"ML token refresh cron error: {type(e).__name__}: {e}")


async def start_ml_refresh_cron():
    """Background task que roda indefinidamente."""
    # Aguarda 60s na startup para o DB estar pronto
    await asyncio.sleep(60)
    while True:
        await run_ml_refresh()
        await asyncio.sleep(INTERVAL_SECONDS)
