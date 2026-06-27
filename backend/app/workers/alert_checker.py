"""
alert_checker.py — Worker que verifica alertas de preço e envia notificações via Telegram

Executar como worker independente:
    python alert_checker.py

Ou integrar ao main.py como background task (lifespan).

Lógica:
  1. A cada intervalo (default: 30 min), carrega alertas ativos com telegram_id
  2. Para cada alerta, busca o preço atual na API
  3. Se preço atual <= target_price → dispara notificação + marca triggered_at
"""

import asyncio
import httpx
import os
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update

from app.core.config import settings

logger = logging.getLogger("alert_checker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DATABASE_URL = settings.DATABASE_URL
TELEGRAM_TOKEN = settings.TELEGRAM_BOT_TOKEN
API_BASE = settings.INTERNAL_API_URL
CHECK_INTERVAL_SECONDS = int(os.getenv("ALERT_CHECK_INTERVAL", "1800"))  # 30 min

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def send_telegram_message(chat_id: str, text: str) -> bool:
    """Envia mensagem via Telegram Bot API."""
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado; notificação ignorada.")
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False},
            )
            ok = r.status_code == 200
            if not ok:
                logger.warning(f"Telegram sendMessage falhou: {r.status_code} {r.text[:200]}")
            return ok
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")
        return False


async def get_current_price(query: str) -> tuple[float | None, str | None, str | None]:
    """
    Busca preço atual na API interna.
    Retorna (preço, link, título) ou (None, None, None) em caso de erro.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{API_BASE}/api/v1/search",
                params={"q": query, "limit": 5},
            )
            if r.status_code != 200:
                return None, None, None
            data = r.json()
            offers = data.get("offers", [])
            if not offers:
                return None, None, None
            # Pega a oferta com menor preço final
            best = min(offers, key=lambda o: o.get("final_price") or o.get("price") or 999999)
            price = best.get("final_price") or best.get("price")
            link = best.get("affiliate_url") or best.get("product_url")
            title = best.get("title", query)
            return price, link, title
    except Exception as e:
        logger.error(f"Erro ao buscar preço para '{query}': {e}")
        return None, None, None


async def check_and_notify(db: AsyncSession):
    """Verifica todos os alertas ativos com telegram_id e dispara notificações."""
    from app.models.models import PriceAlert  # import local para evitar circular

    # Carrega alertas ativos com owner_id definido e ainda não disparados
    stmt = (
        select(PriceAlert)
        .where(
            PriceAlert.is_active == True,
            PriceAlert.owner_id.isnot(None),
            PriceAlert.triggered_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    if not alerts:
        logger.info("Nenhum alerta pendente.")
        return

    logger.info(f"Verificando {len(alerts)} alerta(s)...")

    for alert in alerts:
        current_price, link, title = await get_current_price(alert.query)

        if current_price is None:
            logger.debug(f"Sem preço para '{alert.query}' — pulando.")
            continue

        logger.debug(f"'{alert.query}': atual={current_price:.2f} alvo={alert.target_price:.2f}")

        if current_price <= alert.target_price:
            # Só envia Telegram se owner_id parece um telegram_id real (numérico)
            # bpt_anon_id do browser não é entregue via Telegram, só via e-mail/push futuros
            owner = alert.owner_id
            can_telegram = owner.lstrip("-").isdigit()  # IDs Telegram são numéricos
            savings = alert.target_price - current_price
            msg_lines = [
                "🔔 *Alerta de preço atingido!*",
                "",
                f"🛍️ *{title[:80]}*",
                "",
                f"💵 Preço atual: *R$ {current_price:.2f}*",
                f"🎯 Seu alvo: R$ {alert.target_price:.2f}",
                f"💰 Economia: R$ {savings:.2f}",
            ]
            if link:
                msg_lines += ["", f"👉 [Ver oferta]({link})"]
            msg_lines += ["", "_BestPriceToday — monitoramento de preços_"]

            text = "\n".join(msg_lines)

            sent = False
            if can_telegram:
                sent = await send_telegram_message(owner, text)
            else:
                # owner_id é um bpt_anon_id do browser: apenas marca como processado
                logger.info(f"Alerta {alert.id}: owner anônimo (browser), sem Telegram")
                sent = True

            if sent:
                alert.triggered_at = datetime.now(timezone.utc)
                alert.is_active = False
                await db.flush()
                logger.info(f"✅ Alerta {alert.id} disparado para {owner} ({alert.query})")
            else:
                logger.warning(f"⚠️ Falha ao enviar alerta {alert.id}")

            # Throttle: pausa breve entre mensagens para evitar rate-limit do Telegram
            await asyncio.sleep(0.5)

    await db.commit()


async def run_checker_loop():
    """Loop principal do worker."""
    logger.info(f"Alert checker iniciado. Intervalo: {CHECK_INTERVAL_SECONDS}s")
    while True:
        try:
            async with SessionLocal() as db:
                await check_and_notify(db)
        except Exception as e:
            logger.error(f"Erro no ciclo de verificação: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_checker_loop())
