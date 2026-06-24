"""
Migration manual: adiciona coluna telegram_id na tabela alertas
e torna user_id nullable.

Executar uma vez contra o banco Neon:
  cd backend && venv/bin/python scripts/migrate_alerts.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

SQL_1 = "ALTER TABLE alertas ALTER COLUMN user_id DROP NOT NULL"
SQL_2 = "ALTER TABLE alertas ADD COLUMN IF NOT EXISTS telegram_id VARCHAR"
SQL_3 = "CREATE INDEX IF NOT EXISTS ix_alertas_telegram_id ON alertas (telegram_id)"


async def run():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text(SQL_1))
        await conn.execute(text(SQL_2))
        await conn.execute(text(SQL_3))
    await engine.dispose()
    print("Migration concluída!")


if __name__ == "__main__":
    asyncio.run(run())
