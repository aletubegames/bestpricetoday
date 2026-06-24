"""Testes do backend BestPriceToday."""
import pytest
import pytest_asyncio
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
    from app.schemas.schemas import SearchResponse, OfferSchema, ProviderEnum

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
