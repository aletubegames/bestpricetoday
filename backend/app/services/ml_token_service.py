"""
ML Token Service — manages ML OAuth token lifecycle.

Key behaviors:
- Stores tokens in DB (ml_tokens table)
- auto-refreshes before expiry (5 min buffer)
- refresh_token is single-use: saves the NEW pair after every refresh
- Never logs actual token values
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.config import settings
from app.core.logging import logger
from app.models.models import MLToken


REFRESH_BUFFER_MINUTES = 10  # refresh 10 min before expiry


async def get_token(db: AsyncSession) -> Optional[str]:
    """
    Returns a valid ML access_token.
    Auto-refreshes if within REFRESH_BUFFER_MINUTES of expiry.
    Returns None if no token is stored or refresh fails.
    """
    # Try DB first
    r = await db.execute(select(MLToken).order_by(MLToken.updated_at.desc()).limit(1))
    row = r.scalar()

    if row:
        # Check if still valid (with buffer)
        if row.expires_at > datetime.now(timezone.utc) + timedelta(minutes=REFRESH_BUFFER_MINUTES):
            return row.access_token
        # Needs refresh
        logger.info("ML access_token near expiry, refreshing [token redacted]")
        new_data = await _do_refresh(row.refresh_token)
        if new_data:
            await _save_tokens(db, new_data)
            return new_data["access_token"]
        else:
            logger.warning("ML token refresh failed — user must re-authorize")
            return None

    # Fall back to settings (initial bootstrap)
    if settings.MERCADOLIVRE_ACCESS_TOKEN:
        return settings.MERCADOLIVRE_ACCESS_TOKEN

    return None


async def save_from_oauth(db: AsyncSession, token_data: dict) -> None:
    """Called after successful OAuth callback. Saves initial token pair."""
    await _save_tokens(db, token_data)


async def _save_tokens(db: AsyncSession, data: dict) -> None:
    """Upsert token row. Always saves both access + refresh token. Deletes old rows."""
    user_id = str(data.get("user_id", "default"))
    expires_in = int(data.get("expires_in", 21600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Remove todos os tokens antigos (garante 1 linha só)
    await db.execute(delete(MLToken))

    row = MLToken(
        user_id=user_id,
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=expires_at,
        scope=data.get("scope"),
    )
    db.add(row)
    await db.commit()
    logger.info(f"ML tokens saved for user_id={user_id} expires_at={expires_at} [values redacted]")


async def _do_refresh(refresh_token: str) -> Optional[dict]:
    """Exchange refresh_token for new access+refresh pair."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.MERCADOLIVRE_APP_ID,
                    "client_secret": settings.MERCADOLIVRE_SECRET,
                    "refresh_token": refresh_token,
                },
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"ML refresh failed: HTTP {resp.status_code} [body redacted]")
        return None
    except Exception as e:
        logger.error(f"ML refresh exception: {type(e).__name__} [details redacted]")
        return None


async def get_token_status(db: AsyncSession) -> dict:
    """Returns token status for admin dashboard — never exposes token values."""
    r = await db.execute(select(MLToken).order_by(MLToken.updated_at.desc()).limit(1))
    row = r.scalar()

    if not row:
        # Check settings fallback
        has_env_token = bool(settings.MERCADOLIVRE_ACCESS_TOKEN)
        return {
            "status": "env_only" if has_env_token else "not_configured",
            "source": "environment" if has_env_token else "none",
            "expires_at": None,
            "user_id": None,
            "needs_reauth": not has_env_token,
        }

    now = datetime.now(timezone.utc)
    expires_in_minutes = int((row.expires_at - now).total_seconds() / 60)
    is_expired = row.expires_at <= now
    needs_refresh = row.expires_at <= now + timedelta(minutes=REFRESH_BUFFER_MINUTES)

    return {
        "status": "expired" if is_expired else ("expiring_soon" if needs_refresh else "active"),
        "source": "database",
        "expires_at": row.expires_at.isoformat(),
        "expires_in_minutes": max(0, expires_in_minutes),
        "user_id": row.user_id,
        "updated_at": row.updated_at.isoformat(),
        "needs_reauth": is_expired and not row.refresh_token,
    }
