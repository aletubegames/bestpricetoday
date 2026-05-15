"""
Conversion polling cron — roda a cada hora via startup event ou externo.
"""
import asyncio
from app.core.logging import logger


async def run_conversion_poll():
    """Run once."""
    from app.db.session import AsyncSessionLocal
    from app.integrations.conversion_tracker import poll_all_conversions

    async with AsyncSessionLocal() as db:
        try:
            results = await poll_all_conversions(db)
            logger.info(f"Hourly conversion poll: {results}")
        except Exception as e:
            logger.error(f"Conversion cron error: {e}")


async def start_conversion_cron():
    """Background task that runs every hour."""
    while True:
        await run_conversion_poll()
        await asyncio.sleep(3600)  # 1 hour
