from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safety net: columns added after initial migration that may not exist yet
        # SQLAlchemy create_all() only creates new tables, never alters existing ones.
        # These ALTER TABLE statements bridge the gap until alembic migrations are run.
        missing_columns = [
            ("users", "facebook_id", "VARCHAR UNIQUE"),
            ("users", "updated_at", "TIMESTAMP WITH TIME ZONE"),
            ("users", "deleted_at", "TIMESTAMP WITH TIME ZONE"),
            ("users", "clerk_id", "VARCHAR UNIQUE"),
        ]
        for table, col, col_type in missing_columns:
            try:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}"
                ))
            except Exception:
                pass

        # Missing indexes
        missing_indexes = [
            ("users", "ix_users_facebook_id", "facebook_id"),
            ("users", "ix_users_clerk_id", "clerk_id"),
        ]
        for table, idx_name, col in missing_indexes:
            try:
                await conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"
                ))
            except Exception:
                pass
