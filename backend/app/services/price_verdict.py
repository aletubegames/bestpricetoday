"""
price_verdict.py — Veredito factual "esse desconto é real?" por produto.

Dado o preço atual (AffiliateProduct.price) e os snapshots de
affiliate_price_history, calcula onde o preço está vs. o histórico
medido — nunca opinião sobre a loja, só números com datas.

Série diária: cada recorded_at vira uma data local (America/Sao_Paulo);
quando há mais de um snapshot no mesmo dia, vale o ÚLTIMO.
"""
from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AffiliatePriceHistory, AffiliateProduct

TZ_SP = ZoneInfo("America/Sao_Paulo")

HISTORY_DAYS = 120  # janela buscada por verdicts_for
MIN_PREV_DAYS = 7   # mínimo de dias (fora de hoje) p/ veredito com base em histórico

VERDICT_LABELS = {
    "menor_preco": "Menor preço que já registramos",
    "abaixo_media": "Abaixo da média de 30 dias",
    "normal": "Preço na média — sem desconto real",
    "acima_media": "Acima da média de 30 dias",
    "sem_historico": "Histórico curto — ainda medindo",
}


def _aware_utc(dt: datetime) -> datetime:
    """Normaliza datetime para UTC aware (SQLite devolve naive; assume UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _local_date(dt: datetime) -> date:
    return _aware_utc(dt).astimezone(TZ_SP).date()


def _local_today(now: Optional[datetime]) -> date:
    if now is None:
        now = datetime.now(timezone.utc)
    return _local_date(now)


def compute_verdict(
    current_price: float,
    points: list[tuple[datetime, float]],
    now: Optional[datetime] = None,
) -> dict:
    """Calcula o veredito de preço. Pura — sem DB.

    points: [(recorded_at, price), ...] — snapshots de affiliate_price_history.
    """
    today = _local_today(now)

    # Série diária: último preço de cada dia local, ordenada por data
    last_of_day: dict[date, tuple[datetime, float]] = {}
    for recorded_at, price in points:
        if recorded_at is None or price is None:
            continue
        d = _local_date(recorded_at)
        ts = _aware_utc(recorded_at)
        prev_point = last_of_day.get(d)
        if prev_point is None or ts > prev_point[0]:
            last_of_day[d] = (ts, float(price))

    daily = sorted((d, p) for d, (_, p) in last_of_day.items())
    daily_dates = [d for d, _ in daily]

    # prev = dias anteriores a hoje (hoje não entra em min/mediana)
    prev = [(d, p) for d, p in daily if d < today]
    # Fallback de estatísticas quando não há nenhum dia anterior: usa a série toda
    stats_source = prev if prev else daily
    stat_prices = [p for _, p in stats_source]

    days_monitored = len(daily)
    first_date = daily_dates[0] if daily_dates else None

    if stat_prices:
        min_price = min(stat_prices)
        min_date = max(d for d, p in stats_source if p == min_price)
        max_price = max(stat_prices)
    else:
        min_price = min_date = max_price = None

    cutoff30 = today - timedelta(days=30)
    last30 = [p for d, p in prev if d >= cutoff30]
    if len(last30) >= 5:
        median_30 = statistics.median(last30)
    elif prev:
        median_30 = statistics.median([p for _, p in prev])
    elif daily:
        median_30 = statistics.median([p for _, p in daily])
    else:
        median_30 = None

    current = float(current_price) if current_price is not None else 0.0

    verdict = "sem_historico"
    # Sem preço atual (ou histórico curto) não dá pra afirmar desconto real
    if current > 0 and len(prev) >= MIN_PREV_DAYS and min_price is not None and median_30:
        if current <= min_price + 0.01 and current <= median_30 * 0.97:
            verdict = "menor_preco"
        elif current <= median_30 * 0.95:
            verdict = "abaixo_media"
        elif current >= median_30 * 1.05:
            verdict = "acima_media"
        else:
            verdict = "normal"

    # Subida recente: dias < hoje-21d (older) vs. últimos 21d (recent, sem hoje).
    # Pico = 2º maior preço diário da janela: um spike de 1 dia (erro de
    # coleta) não pode virar "subiu X%" — o nível tem que ter durado ≥2 dias.
    rise_pct_21d = None
    cutoff21 = today - timedelta(days=21)
    older = [p for d, p in prev if d < cutoff21]
    recent = [p for d, p in prev if d >= cutoff21]
    if len(older) >= 5 and len(recent) >= 2:
        peak = sorted(recent)[-2]
        rise = peak / statistics.median(older) - 1
        if rise >= 0.10:
            rise_pct_21d = round(rise * 100, 1)

    # O badge "subiu" alerta preço inflado antes do desconto — só faz
    # sentido quando o preço atual NÃO está baixo (menor/média).
    if verdict in ("menor_preco", "abaixo_media"):
        rise_pct_21d = None

    pct_vs_median = None
    if median_30:
        pct_vs_median = round((1 - current / median_30) * 100, 1)

    sparkline = [
        {"d": d.isoformat(), "p": float(p)}
        for d, p in daily[-90:]
    ]

    return {
        "verdict": verdict,
        "verdict_label": VERDICT_LABELS[verdict],
        "current_price": current,
        "min_price": float(min_price) if min_price is not None else None,
        "min_date": min_date.isoformat() if min_date else None,
        "max_price": float(max_price) if max_price is not None else None,
        "median_30": float(median_30) if median_30 is not None else None,
        "pct_vs_median": pct_vs_median,
        "days_monitored": days_monitored,
        "first_date": first_date.isoformat() if first_date else None,
        "rise_pct_21d": rise_pct_21d,
        "sparkline": sparkline,
    }


async def verdicts_for(db: AsyncSession, products: list) -> dict[uuid.UUID, dict]:
    """Vereditos de vários produtos numa única query de histórico (últimos 120d)."""
    ids = [p.id for p in products if getattr(p, "id", None) is not None]
    if not ids:
        return {}

    since = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    stmt = (
        select(
            AffiliatePriceHistory.product_id,
            AffiliatePriceHistory.recorded_at,
            AffiliatePriceHistory.price,
        )
        .where(
            AffiliatePriceHistory.product_id.in_(ids),
            AffiliatePriceHistory.recorded_at >= since,
        )
        .order_by(AffiliatePriceHistory.recorded_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    by_product: dict[uuid.UUID, list[tuple[datetime, float]]] = {}
    for pid, recorded_at, price in rows:
        by_product.setdefault(pid, []).append((recorded_at, float(price)))

    now = datetime.now(timezone.utc)
    out: dict[uuid.UUID, dict] = {}
    for p in products:
        pid = getattr(p, "id", None)
        if pid is None:
            continue
        price = getattr(p, "price", None)
        out[pid] = compute_verdict(price if price is not None else 0.0, by_product.get(pid, []), now=now)
    return out
