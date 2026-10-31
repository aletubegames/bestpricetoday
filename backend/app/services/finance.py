from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.models.models import AffiliateMetricsSnapshot, ConversionEvent


FINANCE_PROVIDERS = ("mercadolivre", "amazon", "shopee", "aliexpress", "lomadee", "awin", "kabum")
REGISTERED_STATUSES = ("pending", "confirmed", "approved")


def report_start(days: int, now: datetime) -> datetime:
    if days == 1:
        return now.astimezone(ZoneInfo("America/Sao_Paulo")).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
    return now - timedelta(days=days)


def _money(value) -> Decimal | None:
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return amount if amount.is_finite() else None


def _sum_money(values) -> float | None:
    amounts = [amount for value in values if (amount := _money(value)) is not None]
    return float(sum(amounts, Decimal("0")).quantize(Decimal("0.01"))) if amounts else None


def _aware(value) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)


def _sort_ts(value) -> datetime:
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _snapshot_period(snapshot) -> tuple[datetime, datetime] | None:
    raw = snapshot.raw_data if isinstance(snapshot.raw_data, dict) else {}
    if raw.get("period_source") != "requested_dashboard_filter":
        return None
    start, end = _aware(raw.get("period_start")), _aware(raw.get("period_end"))
    if start is None or end is None or start >= end:
        return None
    return start, end


def _snapshot_reference(snapshot) -> dict | None:
    if snapshot is None:
        return None
    period = _snapshot_period(snapshot)
    label = snapshot.period_until
    if not label and period:
        label = f"{period[0].isoformat()} — {period[1].isoformat()}"
    return {
        "collected_at": snapshot.collected_at.isoformat() if snapshot.collected_at else None,
        "period_until": label,
        "estimated_earnings": _sum_money([snapshot.estimated_earnings]),
        "confirmed_earnings": _sum_money([snapshot.confirmed_earnings]),
        "clicks": snapshot.clicks,
        "orders": snapshot.orders,
    }


def _snapshot_totals(snapshots, start: datetime, end: datetime) -> tuple[dict, list[str]]:
    periods = {}
    unknown_periods = 0
    for snapshot in sorted(snapshots, key=lambda s: (_sort_ts(s.collected_at), str(s.id))):
        period = _snapshot_period(snapshot)
        if period is None:
            unknown_periods += 1
        elif start <= period[0] and period[1] <= end:
            periods[period] = snapshot
    notes = []
    if unknown_periods:
        notes.append(
            f"{unknown_periods} coleta(s) sem intervalo normalizado: referências separadas, não somadas."
        )
    ordered = sorted(periods)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        notes.append("Há períodos sobrepostos no portal; a soma foi suspensa para evitar duplicidade.")
        return {"estimated_commission": None, "approved_commission": None}, notes
    selected = [periods[period] for period in ordered]
    if not selected:
        notes.append("Sem relatório com intervalo inteiramente contido no período selecionado.")
    else:
        notes.append(
            "Somente intervalos completos solicitados ao portal; coletas repetidas usam a versão mais recente."
        )
        if any(s.estimated_earnings is None for s in selected):
            notes.append("Há coletas sem valor estimado; o total disponível é parcial.")
    return {
        "estimated_commission": _sum_money(s.estimated_earnings for s in selected),
        "approved_commission": _sum_money(s.confirmed_earnings for s in selected),
    }, notes


def build_finance_report(conversions, snapshots, days: int, provider: str | None, now: datetime) -> dict:
    start = report_start(days, now)
    selected_providers = {provider} if provider else set(FINANCE_PROVIDERS)
    events_by_provider = defaultdict(dict)
    snapshots_by_provider = defaultdict(list)
    for event in sorted(conversions, key=lambda e: (_sort_ts(e.converted_at), str(e.id))):
        if provider and event.provider != provider:
            continue
        if not isinstance(event.converted_at, datetime) or not start <= event.converted_at < now:
            continue
        name = event.provider or "unknown"
        selected_providers.add(name)
        identity = event.external_order_id or str(event.id)
        events_by_provider[name][identity] = event
    for snapshot in snapshots:
        if provider and snapshot.provider != provider:
            continue
        if not isinstance(snapshot.collected_at, datetime) or snapshot.collected_at > now:
            continue
        name = snapshot.provider or "unknown"
        selected_providers.add(name)
        snapshots_by_provider[name].append(snapshot)

    rows = []
    for name in sorted(selected_providers):
        events = list(events_by_provider[name].values())
        history = sorted(
            snapshots_by_provider[name],
            key=lambda s: (_sort_ts(s.collected_at), str(s.id)), reverse=True,
        )
        notes = []
        if events:
            estimated_events = [e for e in events if e.status == "pending"]
            approved_events = [e for e in events if e.status in ("confirmed", "approved")]
            amounts = {
                "estimated_commission": _sum_money(e.commission_value for e in estimated_events)
                if estimated_events else 0.0,
                "approved_commission": _sum_money(e.commission_value for e in approved_events)
                if approved_events else 0.0,
            }
            source = "conversion_events"
            notes.append("Período pela data de registro da conversão, não pela data de pagamento.")
            notes.append("Aprovadas no sistema = estados confirmed/approved importados; não comprovam repasse.")
            if any(e.status not in REGISTERED_STATUSES for e in events):
                notes.append("Canceladas, rejeitadas e estados desconhecidos não compõem as comissões.")
            if any(e.commission_value is None for e in estimated_events + approved_events):
                notes.append("Há conversões sem valor de comissão; o total disponível é parcial.")
            if history:
                notes.append("Snapshots do portal são referências alternativas, não somados às conversões.")
        elif history:
            amounts, notes = _snapshot_totals(history, start, now)
            source = "affiliate_metrics_snapshots"
        else:
            amounts = {"estimated_commission": None, "approved_commission": None}
            source = "unavailable"
            notes.append("Sem registros financeiros importados; ausência de dado não significa receita zero.")
        notes.append("Pagamento efetivo não informado: não há extrato de repasses integrado nesta fonte.")
        positive_snapshot = next(
            (s for s in history if (_money(s.estimated_earnings) or Decimal("0")) > 0), None
        )
        rows.append({
            "provider": name,
            "source": source,
            "record_count": len(events),
            **amounts,
            "paid_commission": None,
            "notes": notes,
            "latest_snapshot": _snapshot_reference(history[0]) if history else None,
            "historical_snapshot": _snapshot_reference(positive_snapshot),
        })
    return {
        "period_days": days,
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
        "partial": True,
        "totals": {
            "estimated_commission": _sum_money(row["estimated_commission"] for row in rows),
            "approved_commission": _sum_money(row["approved_commission"] for row in rows),
            "paid_commission": None,
        },
        "providers": rows,
        "notes": [
            "Valores disponíveis no site e nas integrações; cobertura parcial, não um extrato bancário.",
            "Estimadas e aprovadas são separadas. Aprovada não significa efetivamente paga.",
            "Referências históricas do portal não são somadas sem um intervalo verificável e não sobreposto.",
            "Sem repasses e custos completos, lucro líquido e ROI não podem ser apurados.",
        ],
    }


async def load_finance_report(db, days: int, provider: str | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    events_query = select(ConversionEvent).where(
        ConversionEvent.converted_at >= report_start(days, now),
        ConversionEvent.converted_at < now,
    )
    snapshots_query = select(AffiliateMetricsSnapshot).where(
        AffiliateMetricsSnapshot.collected_at <= now
    )
    if provider:
        events_query = events_query.where(ConversionEvent.provider == provider)
        snapshots_query = snapshots_query.where(AffiliateMetricsSnapshot.provider == provider)
    events = (await db.execute(events_query)).scalars().all()
    snapshots = (await db.execute(snapshots_query)).scalars().all()
    return build_finance_report(events, snapshots, days, provider, now)
