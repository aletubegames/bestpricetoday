"""
ml_refresh_cron.py — Renova o token OAuth ML de verdade no alaserver.

BUG histórico (11 semanas):
  Cron logava "renovado com sucesso" sem chamar a API do ML.
  get_token() entre 30–60min devolvia o token velho. Logs: 186 falsos vs 63 reais.

Agora:
  - force_refresh() real quando live falha ou < 60min
  - sucesso só se expiry pular (~6h)
  - Telegram se falhar (debounced 6h) — reauth obrigatório
  - NÃO é a sessão de afiliados/cookies (ml_session_keeper / VNC)
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.logging import logger

INTERVAL_SECONDS = 15 * 60
HEAL_THRESHOLD_MINUTES = 60
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ALERT_SENT_FILE = BACKEND_DIR / ".ml_oauth_alert_sent"
ALERT_COOLDOWN_SECONDS = 6 * 3600  # não spamma a cada 15min


async def _send_telegram(msg: str) -> None:
    try:
        from app.core.config import settings

        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = str(settings.TELEGRAM_ALERT_CHAT_ID or "5899118807")
        if not token:
            logger.warning("ML oauth alert: TELEGRAM_BOT_TOKEN vazio")
            return
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"},
            )
        logger.info("ML oauth alert: Telegram enviado")
    except Exception as e:
        logger.warning(f"ML oauth alert Telegram falhou: {type(e).__name__}")


def _should_alert() -> bool:
    if not ALERT_SENT_FILE.exists():
        return True
    try:
        age = datetime.now(timezone.utc).timestamp() - ALERT_SENT_FILE.stat().st_mtime
        return age >= ALERT_COOLDOWN_SECONDS
    except Exception:
        return True


def _mark_alert_sent() -> None:
    try:
        ALERT_SENT_FILE.write_text(datetime.now(timezone.utc).isoformat())
    except Exception:
        pass


def _clear_alert() -> None:
    try:
        ALERT_SENT_FILE.unlink(missing_ok=True)
    except Exception:
        pass


async def _alert_reauth(reason: str, status: dict | None = None) -> None:
    if not _should_alert():
        logger.info(f"ML oauth alert suprimido (cooldown): {reason}")
        return
    st = status or {}
    msg = (
        "🚨 *TOKEN OAUTH ML FALHOU*\n\n"
        f"Motivo: `{reason}`\n"
        f"status: `{st.get('status')}` live_ok: `{st.get('live_ok')}`\n"
        f"expira_em: `{st.get('expires_in_minutes')}` min\n\n"
        "Refresh automático NÃO conseguiu renovar.\n"
        "Abre no browser e reautoriza:\n"
        "`https://api.alaserver.com.br/api/v1/auth/ml/authorize`\n\n"
        "_Isso é o token da API OAuth (DB). Não é sessão de afiliados/VNC._"
    )
    await _send_telegram(msg)
    _mark_alert_sent()


async def run_ml_refresh():
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.ml_token_service import force_refresh, get_token_status

        async with AsyncSessionLocal() as db:
            status = await get_token_status(db, probe_live=True, auto_refresh_on_fail=False)

            if status.get("status") == "not_configured":
                logger.warning("ML token refresh cron: token não configurado — OAuth necessário")
                await _alert_reauth("not_configured", status)
                return

            minutes = int(status.get("expires_in_minutes") or 0)
            live_ok = status.get("live_ok")
            live_http = status.get("live_http_status")
            st = status.get("status")

            needs_refresh = (
                st in ("expired", "expiring_soon", "invalid")
                or minutes < HEAL_THRESHOLD_MINUTES
                or (live_ok is False and live_http in (401, 403))
            )

            if not needs_refresh:
                logger.info(
                    f"ML token refresh cron: OK status={st} live_ok={live_ok} expira_em={minutes}min"
                )
                _clear_alert()  # sessão saudável — libera próximo alerta se falhar de novo
                return

            logger.info(
                f"ML token refresh cron: HEAL status={st} live_ok={live_ok} "
                f"http={live_http} expira={minutes}min — force_refresh REAL"
            )
            before = minutes
            token = await force_refresh(db)
            if not token:
                logger.error("ML token refresh cron: force_refresh FALHOU — reauth necessário")
                await _alert_reauth("force_refresh_failed", status)
                return

            after_status = await get_token_status(db, probe_live=True, auto_refresh_on_fail=False)
            after = int(after_status.get("expires_in_minutes") or 0)

            if after >= before + 30 or after >= 300:
                logger.info(
                    f"ML token refresh cron: REFRESH REAL OK "
                    f"before={before}min after={after}min live_ok={after_status.get('live_ok')}"
                )
                _clear_alert()
            else:
                logger.error(
                    f"ML token refresh cron: SUSPEITO — expiry quase igual "
                    f"(before={before} after={after}). Não contar como sucesso."
                )
                await _alert_reauth(
                    f"suspicious_expiry before={before} after={after}",
                    after_status,
                )
    except Exception as e:
        logger.error(f"ML token refresh cron error: {type(e).__name__}: {e}")


async def start_ml_refresh_cron():
    """Background no bestprice-backend (alaserver 192.168.15.45)."""
    await asyncio.sleep(60)
    while True:
        await run_ml_refresh()
        await asyncio.sleep(INTERVAL_SECONDS)
