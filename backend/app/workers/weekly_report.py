"""Weekly report — resumo de métricas reais no Telegram do dono.

Automatiza a "revisão semanal" do PLANO_RENDA.md §4: cliques humanos
(crawlers filtrados), pedidos/ganhos do portal ML e conversões registradas.
Envia segunda-feira ~9h local, 1x por semana.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import and_, func, or_, select

from app.core.config import settings
from app.core.logging import logger

CHECK_INTERVAL_S = 3600  # 1h — acorda pouco, manda 1x/segunda


async def _send(msg: str):
    """Mensagem pro dono — mesmo padrão de alerta do ml_scraper/distributor."""
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = str(settings.TELEGRAM_ALERT_CHAT_ID or "5899118807")
        if not token:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown",
                      "disable_web_page_preview": True},
            )
        logger.info("Weekly report enviado")
    except Exception as e:
        logger.warning(f"Weekly report: falha ao enviar Telegram: {e}")


async def _build_report() -> str:
    from app.db.session import AsyncSessionLocal
    from app.models.models import (
        AffiliateMetricsSnapshot, AffiliateProduct, ClickEvent, ConversionEvent,
    )
    from app.services.click_integrity import BOT_UA_PATTERNS

    since = datetime.now(timezone.utc) - timedelta(days=7)
    ua_ok = and_(*[~ClickEvent.user_agent.ilike(f"%{p}%") for p in BOT_UA_PATTERNS])
    ip_ok = or_(
        ClickEvent.ip_address.is_(None),
        ~ClickEvent.ip_address.ilike("2a03:2880%"),  # range de crawler da Meta
    )

    async with AsyncSessionLocal() as db:
        clicks = (await db.execute(
            select(func.count()).select_from(ClickEvent)
            .where(ClickEvent.clicked_at >= since, ua_ok, ip_ok)
        )).scalar() or 0

        by_src = (await db.execute(
            select(ClickEvent.source, func.count().label("n"))
            .where(ClickEvent.clicked_at >= since, ua_ok, ip_ok)
            .group_by(ClickEvent.source)
            .order_by(func.count().desc()).limit(5)
        )).all()

        conv = (await db.execute(
            select(func.count()).select_from(ConversionEvent)
            .where(ConversionEvent.converted_at >= since)
        )).scalar() or 0

        products = (await db.execute(
            select(func.count()).select_from(AffiliateProduct)
            .where(AffiliateProduct.is_active == True)
        )).scalar() or 0

        ml = (await db.execute(
            select(AffiliateMetricsSnapshot)
            .where(AffiliateMetricsSnapshot.provider == "mercadolivre")
            .order_by(AffiliateMetricsSnapshot.collected_at.desc())
            .limit(1)
        )).scalar()

    src_txt = ", ".join(f"{s or '?'}:{n}" for s, n in by_src) or "—"
    ml_txt = "—"
    if ml:
        ml_txt = (f"{ml.clicks or 0} cliques / {ml.orders or 0} pedidos / "
                  f"R${ml.estimated_earnings or 0:.2f} estimado / "
                  f"R${ml.confirmed_earnings or 0:.2f} confirmado")

    goal_pct = min(100, round(clicks / 50 * 100))
    return (
        f"📊 *BestPrice — resumo semanal*\n\n"
        f"👆 Cliques humanos (7d): *{clicks}*  (meta F1: 50/sem → {goal_pct}%)\n"
        f"   └ por origem: {src_txt}\n"
        f"🛒 Portal ML (último snapshot): {ml_txt}\n"
        f"✅ Conversões registradas (7d): {conv}\n"
        f"📦 Catálogo ativo: {products}\n\n"
        f"🔥 /hoje: https://bestpricetoday.alaserver.com.br/hoje"
    )


async def run_weekly_report_loop():
    """Toda segunda entre 9h e 9h59 (local) envia o resumo — 1x por semana."""
    logger.info("Weekly report loop started (segundas ~9h)")
    sent_week = None  # "2026-W43" — dedup em memória (reinício → no máximo reenvia 1x)

    while True:
        try:
            now = datetime.now()
            week_key = f"{now.year}-W{now.isocalendar().week}"
            if now.weekday() == 0 and now.hour == 9 and sent_week != week_key:
                await _send(await _build_report())
                sent_week = week_key
        except Exception as e:
            logger.error(f"Weekly report error: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_S)
