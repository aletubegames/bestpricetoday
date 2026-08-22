"""
ML Token Service — manages ML OAuth token lifecycle on alaserver.

Root causes fixed (11 semanas de falhas):
1. Cron dizia "renovado com sucesso" quando get_token() só DEVOLVIA o token
   antigo (buffer 30min) — log mentia (186 falsos vs 63 reais nos logs).
2. refresh_token do ML é single-use: refreshes concorrentes matam a sessão.
3. Sem probe live: token no DB com expiry futuro mas revogado = 401 silencioso.

Comportamento atual:
- force_refresh() SEMPRE troca o refresh_token (com asyncio.Lock)
- health live GET /users/me
- se 401/403 → force_refresh
- nunca loga "sucesso" sem API refresh real + save no DB
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.models import MLToken

REFRESH_BUFFER_MINUTES = 60  # renova com 1h de antecedência (token ML ~6h)
TOKEN_ENCRYPTION_PREFIX = "aesgcm:v1:"
ML_USERS_ME_URL = "https://api.mercadolibre.com/users/me"
ML_OAUTH_URL = "https://api.mercadolibre.com/oauth/token"

# Single-use refresh_token: serializa TODAS as trocas no processo
_refresh_lock = asyncio.Lock()


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


def _norm_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def probe_token_live(access_token: str) -> dict:
    """Live health against ML API."""
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(
                ML_USERS_ME_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code == 200:
            return {"ok": True, "http_status": 200, "reason": "alive"}
        if resp.status_code in (401, 403):
            return {"ok": False, "http_status": resp.status_code, "reason": "unauthorized"}
        return {
            "ok": False,
            "http_status": resp.status_code,
            "reason": f"unexpected_status_{resp.status_code}",
        }
    except Exception as e:
        logger.warning(f"ML live probe exception: {type(e).__name__}")
        return {"ok": False, "http_status": 0, "reason": f"network_error:{type(e).__name__}"}


async def _get_token_row(db: AsyncSession) -> Optional[MLToken]:
    r = await db.execute(select(MLToken).order_by(MLToken.updated_at.desc()).limit(1))
    return r.scalar()


async def _do_refresh(refresh_token: str) -> Optional[dict]:
    """Exchange refresh_token (single-use) for a new pair."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                ML_OAUTH_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.MERCADOLIVRE_APP_ID,
                    "client_secret": settings.MERCADOLIVRE_SECRET,
                    "refresh_token": refresh_token,
                },
            )
        if resp.status_code == 200:
            data = resp.json()
            if not data.get("access_token") or not data.get("refresh_token"):
                logger.error("ML refresh response missing required fields")
                return None
            logger.info("ML refresh API call successful - new tokens received")
            return data
        if resp.status_code == 400:
            body = resp.text[:300]
            logger.error(f"ML refresh failed invalid_grant/400 [body redacted len={len(body)}]")
        else:
            logger.warning(f"ML refresh failed: HTTP {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"ML refresh exception: {type(e).__name__}")
        return None


async def _save_tokens(db: AsyncSession, data: dict) -> None:
    """Replace token row. Must succeed after API refresh or session is lost."""
    user_id = str(data.get("user_id", "default"))
    expires_in = int(data.get("expires_in", 21600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    try:
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
        logger.info(
            f"ML tokens saved successfully for user_id={user_id} "
            f"expires_at={expires_at.isoformat()} expires_in={expires_in}s [values redacted]"
        )
    except Exception as e:
        logger.error(
            f"CRITICAL: Failed to save ML tokens after refresh — "
            f"session may be lost: {type(e).__name__}"
        )
        await db.rollback()
        raise


async def force_refresh(db: AsyncSession) -> Optional[str]:
    """Always exchange refresh_token. Serialized via lock (single-use).

    Returns new access_token only if API refresh + DB save both succeeded.
    """
    async with _refresh_lock:
        row = await _get_token_row(db)
        if not row:
            logger.warning("force_refresh: no ML token in database")
            return None

        refresh_token = _decrypt_token(row.refresh_token)
        if not refresh_token:
            logger.error("force_refresh: refresh_token decrypt failed - reauth required")
            return None

        old_expires = _norm_dt(row.expires_at)
        logger.info("ML force_refresh: exchanging refresh_token [redacted]")
        new_data = await _do_refresh(refresh_token)
        if not new_data:
            logger.warning("ML force_refresh failed — user must re-authorize")
            return None

        # Preserve user_id from DB if API omits it
        if not new_data.get("user_id") and row.user_id:
            new_data["user_id"] = row.user_id

        await _save_tokens(db, new_data)

        # Verify save
        saved = await _get_token_row(db)
        if not saved:
            logger.error("force_refresh: save verification failed - row missing")
            return None
        new_expires = _norm_dt(saved.expires_at)
        if old_expires and new_expires and new_expires <= old_expires:
            logger.error(
                f"force_refresh: expiry did not advance "
                f"(old={old_expires.isoformat()} new={new_expires.isoformat()})"
            )
        return new_data["access_token"]


async def get_token(db: AsyncSession, *, probe_live: bool = False) -> Optional[str]:
    """Return valid access_token; force_refresh if near expiry or live health fails."""
    row = await _get_token_row(db)
    if not row:
        logger.warning("No ML token in database - user must authenticate via OAuth flow")
        return None

    access_token = _decrypt_token(row.access_token)
    refresh_token = _decrypt_token(row.refresh_token)
    if not access_token or not refresh_token:
        logger.error("ML token exists in DB but decryption failed - reauth required")
        return None

    expires_at = _norm_dt(row.expires_at)
    now = datetime.now(timezone.utc)
    needs_time_refresh = expires_at is None or expires_at <= now + timedelta(minutes=REFRESH_BUFFER_MINUTES)

    if needs_time_refresh:
        logger.info(
            f"ML access_token near expiry "
            f"(expires_in_min={(expires_at - now).total_seconds() / 60 if expires_at else -1:.0f}) "
            f"— force_refresh"
        )
        return await force_refresh(db)

    if probe_live:
        live = await probe_token_live(access_token)
        if live["ok"]:
            return access_token
        if live.get("http_status") in (401, 403):
            logger.warning(
                f"ML live health failed ({live.get('http_status')}/{live.get('reason')}) — force_refresh"
            )
            return await force_refresh(db)
        logger.warning(f"ML live health degraded (no refresh): {live}")
        return access_token

    return access_token


async def save_from_oauth(db: AsyncSession, token_data: dict) -> None:
    await _save_tokens(db, token_data)


def _status_from_row(row: MLToken) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = _norm_dt(row.expires_at)
    updated_at = _norm_dt(row.updated_at)

    expires_in_minutes = int((expires_at - now).total_seconds() / 60) if expires_at else 0
    is_expired = expires_at is None or expires_at <= now
    needs_refresh = expires_at is None or expires_at <= now + timedelta(minutes=REFRESH_BUFFER_MINUTES)
    has_refresh = bool(_decrypt_token(row.refresh_token))

    return {
        "status": "expired" if is_expired else ("expiring_soon" if needs_refresh else "active"),
        "source": "database",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expires_in_minutes": max(0, expires_in_minutes),
        "user_id": row.user_id,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "needs_reauth": is_expired and not has_refresh,
    }


async def get_token_status(
    db: AsyncSession,
    *,
    probe_live: bool = False,
    auto_refresh_on_fail: bool = False,
) -> dict:
    """Status for admin/health. auto_refresh_on_fail uses force_refresh under lock."""
    row = await _get_token_row(db)

    if not row:
        return {
            "status": "not_configured",
            "source": "none",
            "expires_at": None,
            "user_id": None,
            "needs_reauth": True,
            "message": "No ML token in database - user must authenticate via OAuth flow",
            "live_ok": False,
            "auto_refreshed": False,
        }

    status = _status_from_row(row)
    status["live_ok"] = None
    status["auto_refreshed"] = False
    status["live_reason"] = None
    status["live_http_status"] = None

    access_token = _decrypt_token(row.access_token)
    should_heal = auto_refresh_on_fail and status["status"] in ("expired", "expiring_soon")

    if probe_live and access_token:
        live = await probe_token_live(access_token)
        status["live_ok"] = live["ok"]
        status["live_reason"] = live.get("reason")
        status["live_http_status"] = live.get("http_status")
        if not live["ok"] and live.get("http_status") in (401, 403):
            should_heal = auto_refresh_on_fail
            if status["status"] == "active":
                status["status"] = "invalid"

    if should_heal:
        logger.info(
            f"ML health heal: status={status['status']} live_ok={status.get('live_ok')} — force_refresh"
        )
        new_token = await force_refresh(db)
        status["auto_refreshed"] = bool(new_token)
        if new_token:
            row = await _get_token_row(db)
            if row:
                status = _status_from_row(row)
                status["auto_refreshed"] = True
                if probe_live:
                    live2 = await probe_token_live(new_token)
                    status["live_ok"] = live2["ok"]
                    status["live_reason"] = live2.get("reason")
                    status["live_http_status"] = live2.get("http_status")
                    if not live2["ok"]:
                        status["status"] = "invalid"
                        status["needs_reauth"] = True
        else:
            status["needs_reauth"] = True
            if status["status"] not in ("not_configured",):
                status["status"] = "expired"

    return status
