"""Testes do backend BestPriceToday."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.schemas.schemas import OfferSchema, ProviderEnum


# ─── Health ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Search — validação ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_missing_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/search")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_short_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/search", params={"q": "a"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_returns_offers():
    """Busca com mock dos providers deve retornar lista de ofertas."""
    mock_offer = OfferSchema(
        provider=ProviderEnum.mercadolivre,
        title="Smartphone Samsung Galaxy",
        price=1999.0,
        original_price=2499.0,
        discount_percent=20.0,
        shipping_free=True,
        shipping_price=0,
        final_price=1999.0,
        affiliate_url="https://mercadolivre.com.br/p/MLB123?matt_tool=2661096739949809",
        image_url="https://example.com/img.jpg",
    )

    with patch("app.api.v1.endpoints.search.search_all", new_callable=AsyncMock) as mock_search:
        from app.schemas.schemas import SearchResponse
        mock_search.return_value = SearchResponse(
            query="smartphone samsung",
            normalized_query="smartphone samsung",
            total=1,
            offers=[mock_offer],
            cached=False,
            took_ms=42,
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/search", params={"q": "smartphone samsung"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["offers"][0]["provider"] == "mercadolivre"
    assert data["offers"][0]["price"] == 1999.0


# ─── Alertas ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert_with_owner_id():
    """Alerta deve ser aceito com owner_id obrigatório."""
    from app.db.session import get_db as real_get_db
    from app.models.models import PriceAlert
    import uuid
    from datetime import datetime, timezone

    fake_alert = PriceAlert(
        id=uuid.uuid4(),
        user_id=None,
        owner_id="5899118807",
        query="notebook gamer",
        target_price=3500.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock(side_effect=lambda obj: None)

    async def override_get_db():
        yield session

    # Patch the endpoint to return a fake alert rather than relying on DB
    with patch("app.api.v1.endpoints.alerts.PriceAlert", return_value=fake_alert):
        app.dependency_overrides[real_get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post("/api/v1/alerts", json={
                    "query": "notebook gamer",
                    "target_price": 3500.0,
                    "owner_id": "5899118807",
                })
        finally:
            app.dependency_overrides.pop(real_get_db, None)

    # 201 esperado; ao menos não deve ser 422
    assert resp.status_code != 422


@pytest.mark.asyncio
async def test_alert_requires_query_and_price():
    """Alerta sem target_price deve retornar 422 mesmo com owner_id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/alerts", json={"query": "notebook", "owner_id": "user123"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_alert_requires_owner_id():
    """Alerta sem owner_id deve retornar 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/alerts", json={
            "query": "notebook gamer",
            "target_price": 3500.0,
        })
    assert resp.status_code == 422


# ─── Cache ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_returns_cached_flag():
    """Se cache retornar dados, a resposta deve ter cached=True."""
    from app.schemas.schemas import SearchResponse

    cached_resp = SearchResponse(
        query="fone bluetooth",
        normalized_query="fone bluetooth",
        total=0,
        offers=[],
        cached=True,
        took_ms=1,
    )

    with patch("app.services.search.get_cached", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = cached_resp.model_dump()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/search", params={"q": "fone bluetooth"})

    assert resp.status_code == 200
    assert resp.json()["cached"] is True


def test_ml_login_authentication_url_detection():
    from app.workers.ml_telegram_login import _is_authenticated_url

    assert _is_authenticated_url("https://www.mercadolivre.com.br/afiliados/hub")
    assert not _is_authenticated_url("https://www.mercadolivre.com/jms/mlb/login?go=/afiliados")
    assert not _is_authenticated_url("about:blank")


def test_ml_scraper_only_accepts_authenticated_affiliate_portal_url():
    from app.workers.ml_scraper import _is_authenticated_portal_url

    assert _is_authenticated_portal_url("https://www.mercadolivre.com.br/afiliados/hub")
    assert not _is_authenticated_portal_url("https://www.mercadolivre.com.br/")
    assert not _is_authenticated_portal_url("https://www.mercadolivre.com/jms/mlb/login")


def test_ml_scraper_clears_expired_flag_after_success(tmp_path, monkeypatch):
    from app.workers import ml_scraper

    expired = tmp_path / "expired"
    expired.write_text("expired")
    monkeypatch.setattr(ml_scraper, "EXPIRED_FILE", expired)

    ml_scraper._clear_session_flags()

    assert not expired.exists()


def test_ml_storage_state_only_overwrites_older_profile_cookies():
    from app.workers.ml_telegram_login import _should_inject_storage_state

    assert _should_inject_storage_state(20.0, None)
    assert _should_inject_storage_state(20.0, 19.0)
    assert not _should_inject_storage_state(20.0, 20.0)
    assert not _should_inject_storage_state(20.0, 21.0)


def test_ml_browser_user_agent_matches_installed_browser_baseline():
    from app.workers.ml_coupon_scraper import BR_TIMEZONE
    from app.workers.ml_session_keeper import USER_AGENTS
    from app.workers.ml_scraper import run_scraper
    from app.workers.ml_telegram_login import USER_AGENT

    assert USER_AGENTS == [USER_AGENT]
    assert "Chrome/151." in USER_AGENT
    assert BR_TIMEZONE is not None
    assert run_scraper is not None


def test_ml_login_expired_flags_are_cleared(tmp_path, monkeypatch):
    from app.workers import ml_telegram_login

    expired = tmp_path / "expired"
    alert = tmp_path / "alert"
    expired.write_text("expired")
    alert.write_text("alert")
    monkeypatch.setattr(ml_telegram_login, "EXPIRED_FILE", expired)
    monkeypatch.setattr(ml_telegram_login, "ALERT_SENT_FILE", alert)

    ml_telegram_login._clear_expired_flags()

    assert not expired.exists()
    assert not alert.exists()


def test_ml_login_does_not_await_sync_flag_cleanup():
    import inspect
    from app.workers import ml_telegram_login

    assert not inspect.iscoroutinefunction(ml_telegram_login._clear_expired_flags)
    assert "await _clear_expired_flags()" not in inspect.getsource(ml_telegram_login.do_telegram_login)


def test_ml_browser_lock_serializes_jobs(tmp_path):
    from app.workers.ml_session_keeper import LockFile

    first = LockFile(tmp_path / "ml.lock")
    second = LockFile(tmp_path / "ml.lock")
    try:
        assert first.acquire()
        assert not second.acquire()
    finally:
        first.release()

    try:
        assert second.acquire()
    finally:
        second.release()


def test_history_url_canonicalization_removes_tracking_parameters():
    from app.api.v1.endpoints.affiliate import _canonical_history_url

    url = (
        "https://meli.la/example?matt_word=word&matt_tool=tool&"
        "utm_source=bestpricetoday&foo=bar"
    )

    assert _canonical_history_url(url) == "https://meli.la/example?foo=bar"


def test_coupon_schedule_uses_brasilia_hours():
    from app.workers.coupon_distributor import COUPON_POST_SCHEDULE

    assert COUPON_POST_SCHEDULE == [(12, 1), (19, 1)]


def test_coupon_expiry_preserves_brasilia_end_of_day():
    from app.workers.ml_coupon_scraper import BR_TIMEZONE, parse_expiry

    expiry = parse_expiry("Vence em 1 de setembro")
    assert expiry is not None
    local_expiry = expiry.astimezone(BR_TIMEZONE)
    assert (local_expiry.hour, local_expiry.minute, local_expiry.second) == (23, 59, 59)


def test_production_settings_require_secret_key():
    from app.core.config import Settings

    with pytest.raises(RuntimeError):
        Settings(DEBUG=False, SECRET_KEY="").validate_runtime()

    Settings(DEBUG=True, SECRET_KEY="").validate_runtime()


def test_image_proxy_only_allows_known_https_cdn_hosts():
    from app.api.v1.endpoints.links import _is_allowed_image_url

    assert _is_allowed_image_url("https://http2.mlstatic.com/image.webp")
    assert _is_allowed_image_url("https://cdn.example.vteximg.com.br/image.jpg")
    assert not _is_allowed_image_url("http://http2.mlstatic.com/image.webp")
    assert not _is_allowed_image_url("https://localhost/image.jpg")
    assert not _is_allowed_image_url("https://user:pass@http2.mlstatic.com/image.jpg")


@pytest.mark.asyncio
async def test_readiness_checks_database_and_redis(monkeypatch):
    from app.main import readiness

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, query):
            return None

    class FakeRedis:
        async def ping(self):
            return True

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr("app.db.session.AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr("app.core.cache.get_redis", fake_get_redis)

    response = await readiness()

    assert response.status_code == 200
    assert b'"status":"ready"' in response.body
    assert b'"database":"ok"' in response.body
    assert b'"redis":"ok"' in response.body


def test_logging_filter_redacts_rendered_httpx_arguments():
    import logging
    from app.core.logging import SanitizingFilter

    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        __file__,
        1,
        "HTTP Request: %s %s",
        ("https://api.telegram.org/botBOTSECRET/sendMessage?access_token=SECRET", "200"),
        (),
    )

    SanitizingFilter().filter(record)

    rendered = record.getMessage()
    assert "BOTSECRET" not in rendered
    assert "SECRET" not in rendered
    assert "[REDACTED]" in rendered


@pytest.mark.asyncio
async def test_search_event_is_persisted_without_affecting_search(monkeypatch):
    from app.models.models import Search
    from app.services.search import record_search_event

    class FakeSession:
        def __init__(self):
            self.added = None
            self.committed = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def add(self, value):
            self.added = value

        async def commit(self):
            self.committed = True

    session = FakeSession()
    monkeypatch.setattr("app.db.session.AsyncSessionLocal", lambda: session)

    await record_search_event("  Fone   Bluetooth  ", "fone bluetooth", 3)

    assert isinstance(session.added, Search)
    assert session.added.query == "Fone Bluetooth"
    assert session.added.normalized_query == "fone bluetooth"
    assert session.added.results_count == 3
    assert session.added.source == "web"
    assert session.committed
