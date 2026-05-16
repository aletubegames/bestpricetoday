"""
migration_owner_id.py — Adiciona coluna owner_id às tabelas alertas e favoritos

Execute UMA VEZ no banco de produção (Neon PostgreSQL):
    cd backend && python scripts/migration_owner_id.py

O script é idempotente: verifica se a coluna já existe antes de adicionar.
"""
import asyncio
import os
import sys

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("❌ DATABASE_URL não definida. Configure a variável de ambiente e tente novamente.")
    sys.exit(1)

SQL = """
-- Adiciona owner_id à tabela alertas (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='alertas' AND column_name='owner_id'
    ) THEN
        ALTER TABLE alertas ADD COLUMN owner_id VARCHAR;
        -- Migra telegram_id existente para owner_id
        UPDATE alertas SET owner_id = telegram_id WHERE telegram_id IS NOT NULL;
        -- Define valor padrão para registros sem telegram_id
        UPDATE alertas SET owner_id = 'migrated_' || id::text WHERE owner_id IS NULL;
        -- Torna NOT NULL
        ALTER TABLE alertas ALTER COLUMN owner_id SET NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_alertas_owner_id ON alertas(owner_id);
        RAISE NOTICE 'owner_id adicionado à tabela alertas';
    ELSE
        RAISE NOTICE 'owner_id já existe em alertas';
    END IF;
END $$;

-- Remove telegram_id (agora redundante) — opcional, pode manter por compatibilidade
-- ALTER TABLE alertas DROP COLUMN IF EXISTS telegram_id;

-- Adiciona owner_id à tabela favoritos (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='favoritos' AND column_name='owner_id'
    ) THEN
        ALTER TABLE favoritos ADD COLUMN owner_id VARCHAR;
        -- Registros antigos sem owner (FK user_id era NOT NULL antes): usa fallback
        UPDATE favoritos SET owner_id = 'migrated_' || id::text WHERE owner_id IS NULL;
        ALTER TABLE favoritos ALTER COLUMN owner_id SET NOT NULL;
        -- user_id agora é nullable (removida constraint NOT NULL)
        ALTER TABLE favoritos ALTER COLUMN user_id DROP NOT NULL;
        CREATE INDEX IF NOT EXISTS ix_favoritos_owner_id ON favoritos(owner_id);
        RAISE NOTICE 'owner_id adicionado à tabela favoritos';
    ELSE
        RAISE NOTICE 'owner_id já existe em favoritos';
    END IF;
END $$;
"""


async def run():
    import asyncpg
    print(f"Conectando ao banco...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(SQL)
        print("✅ Migration concluída com sucesso.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
