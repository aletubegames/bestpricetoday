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
import base64
import hashlib
import secrets
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings
from app.core.logging import logger
from app.models.models import MLToken


REFRESH_BUFFER_MINUTES = 30  # refresh 30 min before expiry (increased for safety)
TOKEN_ENCRYPTION_PREFIX = "aesgcm:v1:"


def _token_encryption_key() -> bytes:
    key_material = settings.ML_TOKEN_ENCRYPTION_KEY or settings.secret_key_validated
    return hashlib.sha256(key_material.encode()).digest()


def _encrypt_token(token: str) -> str:
    if token.startswith(TOKEN_ENCRYPTION_PREFIX):
        return token
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_token_encryption_key()).encrypt(nonce, token.encode(), None)
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode()
    return f"{TOKEN_ENCRYPTION_PREFIX}{payload}"


def _decrypt_token(token: str) -> Optional[str]:
    if not token.startswith(TOKEN_ENCRYPTION_PREFIX):
        return token
    try:
        payload = base64.urlsafe_b64decode(token[len(TOKEN_ENCRYPTION_PREFIX):].encode())
        nonce, ciphertext = payload[:12], payload[12:]
        return AESGCM(_token_encryption_key()).decrypt(nonce, ciphertext, None).decode()
    except Exception as exc:
        logger.error(f"ML token decrypt failed: {type(exc).__name__} [details redacted]")
        return None


async def get_token(db: AsyncSession) -> Optional[str]:
    """
    Returns a valid ML access_token.
    Auto-refreshes if within REFRESH_BUFFER_MINUTES of expiry.
    Returns None if no token is stored or refresh fails.
    
    IMPORTANT: No longer falls back to .env token - must use OAuth flow
    to get initial token into database for auto-refresh to work.
    """
    # Try DB first
    r = await db.execute(select(MLToken).order_by(MLToken.updated_at.desc()).limit(1))
    row = r.scalar()

    if row:
        access_token = _decrypt_token(row.access_token)
        refresh_token = _decrypt_token(row.refresh_token)
        if not access_token or not refresh_token:
            logger.error("ML token exists in DB but decryption failed - reauth required")
            return None
        # Check if still valid (with buffer)
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc) + timedelta(minutes=REFRESH_BUFFER_MINUTES):
            return access_token
        # Needs refresh
        logger.info("ML access_token near expiry, refreshing [token redacted]")
        new_data = await _do_refresh(refresh_token)
        if new_data:
            await _save_tokens(db, new_data)
            return new_data["access_token"]
        else:
            logger.warning("ML token refresh failed — user must re-authorize")
            return None

    # No token in DB - user must authenticate via OAuth
    logger.warning("No ML token in database - user must authenticate via OAuth flow")
    return None


async def save_from_oauth(db: AsyncSession, token_data: dict) -> None:
    """Called after successful OAuth callback. Saves initial token pair."""
    await _save_tokens(db, token_data)


async def _save_tokens(db: AsyncSession, data: dict) -> None:
    """Upsert token row. Always saves both access + refresh token. Deletes old rows.
    
    CRITICAL: This must succeed after a refresh, otherwise the old refresh_token
    becomes invalid and user must re-authenticate.
    """
    try:
        user_id = str(data.get("user_id", "default"))
        expires_in = int(data.get("expires_in", 21600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Remove todos os tokens antigos (garante 1 linha só)
        await db.execute(delete(MLToken))

        row = MLToken(
            user_id=user_id,
            access_token=_encrypt_token(data["access_token"]),
            refresh_token=_encrypt_token(data["refresh_token"]),
            expires_at=expires_at,
            scope=data.get("scope"),
        )
        db.add(row)
        await db.commit()
        logger.info(f"ML tokens saved successfully for user_id={user_id} expires_at={expires_at} [values redacted]")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to save ML tokens after refresh - user must re-authenticate: {type(e).__name__}")
        await db.rollback()
        raise


async def _do_refresh(refresh_token: str) -> Optional[dict]:
    """Exchange refresh_token for new access+refresh pair.
    
    IMPORTANT: ML refresh_token is single-use. If this call succeeds but we fail
    to save the new tokens, the old refresh_token becomes invalid and user must re-auth.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
            data = resp.json()
            # Validate response contains required fields
            if not data.get("access_token") or not data.get("refresh_token"):
                logger.error("ML refresh response missing required fields")
                return None
            logger.info("ML refresh API call successful - new tokens received")
            return data
        elif resp.status_code == 400:
            # invalid_grant - refresh token expired or already used
            logger.error(f"ML refresh failed: invalid_grant - refresh token may be expired or already used")
        else:
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
        # No token in database - user must authenticate via OAuth
        return {
            "status": "not_configured",
            "source": "none",
            "expires_at": None,
            "user_id": None,
            "needs_reauth": True,
            "message": "No ML token in database - user must authenticate via OAuth flow"
        }

    now = datetime.now(timezone.utc)
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    updated_at = row.updated_at
    if updated_at and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    expires_in_minutes = int((expires_at - now).total_seconds() / 60)
    is_expired = expires_at <= now
    needs_refresh = expires_at <= now + timedelta(minutes=REFRESH_BUFFER_MINUTES)

    return {
        "status": "expired" if is_expired else ("expiring_soon" if needs_refresh else "active"),
        "source": "database",
        "expires_at": expires_at.isoformat(),
        "expires_in_minutes": max(0, expires_in_minutes),
        "user_id": row.user_id,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "needs_reauth": is_expired and not _decrypt_token(row.refresh_token),
    }
