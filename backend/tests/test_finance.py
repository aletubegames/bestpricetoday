from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.finance import build_finance_report, load_finance_report, report_start


NOW = datetime(2026, 10, 31, 19, tzinfo=timezone.utc)


def event(amount, status="pending", provider="shopee", **kwargs):
    values = {
        "id": uuid4(), "provider": provider, "external_order_id": None,
        "converted_at": NOW - timedelta(days=1),
        "commission_value": amount, "status": status,
    }
    return SimpleNamespace(**(values | kwargs))


def snapshot(amount, start=None, end=None, **kwargs):
    raw = {}
    if start is not None and end is not None:
        raw = {"period_start": start.isoformat(), "period_end": end.isoformat(),
               "period_source": "requested_dashboard_filter"}
    values = {
        "id": uuid4(), "provider": "mercadolivre", "collected_at": NOW - timedelta(hours=1),
        "period_until": None, "clicks": 4, "orders": 0, "estimated_earnings": amount,
        "confirmed_earnings": None, "raw_data": raw,
    }
    return SimpleNamespace(**(values | kwargs))


def row(report, provider):
    return next(item for item in report["providers"] if item["provider"] == provider)


def test_missing_values_are_unknown_not_zero():
    report = build_finance_report([], [], 30, None, NOW)
    assert report["partial"] is True
    assert all(value is None for value in report["totals"].values())
    assert row(report, "amazon")["source"] == "unavailable"
    assert row(report, "amazon")["paid_commission"] is None


def test_pending_approved_rejected_are_not_merged_or_called_paid():
    data = [event("10.10"), event("2.20", "confirmed"), event("3.30", "approved"),
            event("999", "rejected"), event("999", "cancelled"), event("999", "unknown"),
            event("999", "paid")]
    report = build_finance_report(data, [], 7, None, NOW)
    assert report["totals"] == {
        "estimated_commission": 10.10, "approved_commission": 5.50, "paid_commission": None
    }
    assert row(report, "shopee")["record_count"] == 7


def test_period_provider_boundaries_and_future_records():
    data = [event(1), event(2, provider="aliexpress"),
            event(100, converted_at=NOW - timedelta(days=8)),
            event(100, converted_at=NOW), event(100, converted_at=NOW + timedelta(days=1)),
            event(3, converted_at=NOW - timedelta(days=7))]
    report = build_finance_report(data, [], 7, "shopee", NOW)
    assert len(report["providers"]) == 1
    assert report["totals"]["estimated_commission"] == 4
    assert row(report, "shopee")["record_count"] == 2


def test_today_starts_at_brasilia_midnight():
    assert report_start(1, NOW) == datetime(2026, 10, 31, 3, tzinfo=timezone.utc)
    report = build_finance_report(
        [event(100, converted_at=NOW.replace(hour=2)),
         event(3, converted_at=NOW.replace(hour=3))], [], 1, None, NOW
    )
    assert report["totals"]["estimated_commission"] == 3


def test_duplicate_orders_use_latest_status_per_provider():
    first = event(10, external_order_id="same", converted_at=NOW - timedelta(days=2))
    updated = event(12, "confirmed", external_order_id="same")
    other_provider = event(5, provider="aliexpress", external_order_id="same")
    report = build_finance_report([first, updated, other_provider], [], 7, None, NOW)
    assert row(report, "shopee")["record_count"] == 1
    assert report["totals"]["estimated_commission"] == 5
    assert report["totals"]["approved_commission"] == 12


def test_unknown_snapshot_period_is_reference_not_total():
    historic = snapshot(24.53, period_until="31/08-30/09 (reconstruido 30d pos-Neon)")
    latest = snapshot(0, collected_at=NOW)
    report = build_finance_report([], [historic, latest], 30, None, NOW)
    ml = row(report, "mercadolivre")
    assert ml["estimated_commission"] is None
    assert ml["latest_snapshot"]["estimated_earnings"] == 0
    assert ml["historical_snapshot"]["estimated_earnings"] == 24.53
    assert report["totals"]["estimated_commission"] is None


def test_snapshot_same_period_latest_only_and_disjoint_intervals_sum():
    a, b, c = NOW - timedelta(days=3), NOW - timedelta(days=2), NOW - timedelta(days=1)
    report = build_finance_report([], [
        snapshot(10, a, b, collected_at=NOW - timedelta(hours=3)),
        snapshot(12, a, b, collected_at=NOW - timedelta(hours=2)),
        snapshot(8, b, c),
    ], 7, None, NOW)
    assert row(report, "mercadolivre")["estimated_commission"] == 20
    assert row(report, "mercadolivre")["approved_commission"] is None
    assert report["totals"]["paid_commission"] is None


def test_overlapping_nonidentical_snapshot_periods_are_not_summed():
    a, b, c = NOW - timedelta(days=3), NOW - timedelta(days=2), NOW - timedelta(days=1)
    report = build_finance_report([], [snapshot(20, a, c), snapshot(10, b, c)], 7, None, NOW)
    ml = row(report, "mercadolivre")
    assert ml["estimated_commission"] is None
    assert any("sobrepostos" in note for note in ml["notes"])


def test_snapshot_outside_period_future_or_missing_provenance_is_not_total():
    report = build_finance_report([], [
        snapshot(10, NOW - timedelta(days=31), NOW - timedelta(days=29)),
        snapshot(20, NOW - timedelta(days=2), NOW - timedelta(days=1),
                 collected_at=NOW + timedelta(hours=1)),
        snapshot(30, raw_data={"period_start": (NOW - timedelta(days=2)).isoformat(),
                              "period_end": (NOW - timedelta(days=1)).isoformat()}),
    ], 30, None, NOW)
    assert report["totals"]["estimated_commission"] is None


def test_events_and_snapshots_are_alternative_sources_not_added():
    report = build_finance_report([event(7, provider="mercadolivre")], [
        snapshot(20, NOW - timedelta(days=2), NOW - timedelta(days=1)),
    ], 7, None, NOW)
    ml = row(report, "mercadolivre")
    assert ml["source"] == "conversion_events"
    assert ml["estimated_commission"] == 7
    assert ml["latest_snapshot"]["estimated_earnings"] == 20


def test_null_nan_infinity_are_not_money_and_zero_is_known():
    report = build_finance_report(
        [event(None), event(float("nan")), event(float("inf")), event(0, "confirmed")],
        [], 7, "shopee", NOW
    )
    assert report["totals"]["estimated_commission"] is None
    assert report["totals"]["approved_commission"] == 0


@pytest.mark.asyncio
async def test_loader_filters_and_never_writes():
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    await load_finance_report(session, 7, "amazon", NOW)
    statements = [call.args[0] for call in session.execute.call_args_list]
    assert len(statements) == 2
    assert all(statement.is_select for statement in statements)
    assert all("provider" in str(statement) for statement in statements)
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_finance_endpoint_auth_validation_and_real_zero():
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api.v1.endpoints.admin import router, require_admin
    from app.db.session import get_db

    app = FastAPI()
    app.include_router(router, prefix="/admin")
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    async def database():
        yield session

    app.dependency_overrides[get_db] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/admin/finance")
        assert response.status_code in (401, 403)
        app.dependency_overrides[require_admin] = lambda: "test-admin"
        assert (await client.get("/admin/finance?days=0")).status_code == 422
        assert (await client.get("/admin/finance?days=367")).status_code == 422
        assert (await client.get("/admin/finance?provider=invalid")).status_code == 422
        response = await client.get("/admin/finance?days=7&provider=amazon")
        assert response.status_code == 200
        assert response.json()["totals"]["paid_commission"] is None
        assert response.json()["totals"]["estimated_commission"] is None
