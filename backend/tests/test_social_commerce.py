"""Testes das correções sociais/cupons: associação estrita de cupom,
copy segura (coupon_notice), CTAs de perfil e endpoint público /links/social.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.db.session as db_session_module
from app.db.session import Base, get_db
from app.models.models import Coupon, CouponProduct, ShortLink
from app.services.coupon_safety import (
    coupon_from_offer,
    coupon_is_current,
    coupon_notice,
    ml_product_code,
)
from app.workers import coupon_distributor as cd
from app.workers import distributor

NOW = datetime.now(timezone.utc)
FUTURE = NOW + timedelta(days=3)
PAST = NOW - timedelta(days=3)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    tables = [Coupon.__table__, CouponProduct.__table__, ShortLink.__table__]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield Session
    finally:
        await engine.dispose()


def _mk_coupon(**kw) -> Coupon:
    vals = dict(
        id=uuid.uuid4(),
        provider="mercadolivre",
        coupon_code="MLC-T1",
        discount_text="10% OFF",
        discount_percent=10.0,
        expires_at=FUTURE,
        conditions="Válido em itens selecionados",
        store_name="LojaX",
        is_active=True,
    )
    vals.update(kw)
    return Coupon(**vals)


def _mk_cp(coupon_id, ml_code="MLB111", **kw) -> CouponProduct:
    vals = dict(
        coupon_id=coupon_id,
        title="Fone Bluetooth X",
        product_url="https://www.mercadolivre.com.br/p/MLB111",
        ml_code=ml_code,
        is_available=True,
    )
    vals.update(kw)
    return CouponProduct(**vals)


async def _seed(Session, *objs):
    async with Session() as s:
        for o in objs:
            s.add(o)
        await s.commit()


# ─── ml_product_code ─────────────────────────────────────────────────────────

def test_ml_code_normalized():
    assert ml_product_code({"ml_code": "MLB123456"}) == "MLB123456"
    assert ml_product_code({"ml_code": "mlbu-987"}) == "MLBU987"
    assert ml_product_code({"product_id": "mlb-555"}) == "MLB555"
    assert ml_product_code(
        {"product_url": "https://produto.mercadolivre.com.br/MLB-7654-x"}
    ) == "MLB7654"


def test_ml_code_mlb_vs_mlbu_distinct():
    assert ml_product_code({"ml_code": "MLBU123"}) == "MLBU123"
    assert ml_product_code({"ml_code": "MLB123"}) == "MLB123"
    assert ml_product_code({"ml_code": "MLBU123"}) != ml_product_code({"ml_code": "MLB123"})


def test_ml_code_missing_or_embedded():
    assert ml_product_code({}) is None
    assert ml_product_code({"ml_code": None, "product_url": "https://loja.ex/x"}) is None
    assert ml_product_code({"ml_code": "XAMLB12"}) is None


# ─── coupon_is_current / coupon_notice ───────────────────────────────────────

def test_coupon_is_current_requires_verified_and_future():
    assert coupon_is_current({"verified": True, "expires_at": FUTURE}) is True
    assert coupon_is_current({"verified": False, "expires_at": FUTURE}) is False
    assert coupon_is_current({"verified": True, "expires_at": PAST}) is False
    assert coupon_is_current({"verified": True, "expires_at": "bad-date"}) is False
    assert coupon_is_current({"verified": True, "expires_at": None}) is False
    assert coupon_is_current({"verified": True, "expires_at": FUTURE.isoformat()}) is True


def test_coupon_notice_blank_for_unverified_or_expired():
    assert coupon_notice(None) == ""
    assert coupon_notice({"verified": False, "expires_at": FUTURE}) == ""
    assert coupon_notice({"verified": True, "expires_at": PAST, "code": "X"}) == ""


def test_coupon_notice_mlc_has_no_typed_code():
    txt = coupon_notice({
        "verified": True, "code": "MLC-77", "discount_text": "10% OFF",
        "expires_at": FUTURE,
    })
    assert "ativação na conta" in txt
    assert "MLC-77" not in txt
    assert "Confira elegibilidade" in txt


def test_coupon_notice_real_code_with_caveat_and_conditions():
    txt = coupon_notice({
        "verified": True, "code": "LOJA10", "discount_text": "R$ 20 OFF",
        "conditions": "mínimo R$ 100", "expires_at": FUTURE,
    })
    assert "Código informado pela loja: LOJA10" in txt
    assert "Desconto anunciado: R$ 20 OFF" in txt
    assert "Condições: mínimo R$ 100" in txt
    assert "Confira elegibilidade" in txt


# ─── _enrich_offer_with_coupon (SQLite) ─────────────────────────────────────

def _patch_session(monkeypatch, Session):
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", Session)


@pytest.mark.asyncio
async def test_enrich_missing_code_never_queries_db(monkeypatch):
    boom = MagicMock(side_effect=AssertionError("não deveria abrir sessão"))
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", boom)
    offer = {"provider": "mercadolivre", "title": "Produto sem código"}
    out = await distributor._enrich_offer_with_coupon(offer)
    assert "coupon" not in out
    boom.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_strips_caller_coupon_and_does_not_mutate(sqlite_session, monkeypatch):
    _patch_session(monkeypatch, sqlite_session)
    original = {"provider": "mercadolivre", "ml_code": "MLB999", "coupon": {"code": "FAKE"}}
    out = await distributor._enrich_offer_with_coupon(original)
    assert "coupon" not in out
    assert original["coupon"] == {"code": "FAKE"}
    assert "affiliate_url" not in out or out.get("affiliate_url") == original.get("affiliate_url")


@pytest.mark.asyncio
async def test_enrich_amazon_offer_gets_no_arbitrary_coupon(sqlite_session, monkeypatch):
    _patch_session(monkeypatch, sqlite_session)
    coupon = _mk_coupon(provider="amazon", coupon_code="AMZ10")
    cp = _mk_cp(coupon.id, ml_code="MLB111")
    await _seed(sqlite_session, coupon, cp)
    offer = {"provider": "amazon", "ml_code": "MLB111", "seller_name": "LojaX"}
    out = await distributor._enrich_offer_with_coupon(offer)
    assert "coupon" not in out


@pytest.mark.asyncio
async def test_enrich_attaches_only_matching_ml_code(sqlite_session, monkeypatch):
    _patch_session(monkeypatch, sqlite_session)
    coupon = _mk_coupon()
    cp = _mk_cp(coupon.id, ml_code="MLB-111")
    await _seed(sqlite_session, coupon, cp)

    attached = await distributor._enrich_offer_with_coupon(
        {"provider": "mercadolivre", "ml_code": "MLB111", "seller_name": "LojaX"}
    )
    assert attached["coupon"]["code"] == "MLC-T1"
    assert attached["coupon"]["verified"] is True
    assert attached["coupon"]["conditions"] == "Válido em itens selecionados"

    # mesma loja, produto diferente → NÃO anexa
    other = await distributor._enrich_offer_with_coupon(
        {"provider": "mercadolivre", "ml_code": "MLB222", "seller_name": "LojaX"}
    )
    assert "coupon" not in other


@pytest.mark.asyncio
async def test_enrich_expired_coupon_does_not_attach(sqlite_session, monkeypatch):
    _patch_session(monkeypatch, sqlite_session)
    coupon = _mk_coupon(expires_at=PAST)
    cp = _mk_cp(coupon.id, ml_code="MLB111")
    await _seed(sqlite_session, coupon, cp)
    out = await distributor._enrich_offer_with_coupon(
        {"provider": "mercadolivre", "ml_code": "MLB111"}
    )
    assert "coupon" not in out


@pytest.mark.asyncio
async def test_enrich_unavailable_product_does_not_attach(sqlite_session, monkeypatch):
    _patch_session(monkeypatch, sqlite_session)
    coupon = _mk_coupon()
    cp = _mk_cp(coupon.id, ml_code="MLB111", is_available=False)
    await _seed(sqlite_session, coupon, cp)
    out = await distributor._enrich_offer_with_coupon(
        {"provider": "mercadolivre", "ml_code": "MLB111"}
    )
    assert "coupon" not in out


# ─── find_similar_coupon_products ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_find_similar_requires_mercadolivre_and_returns_conditions(sqlite_session, monkeypatch):
    monkeypatch.setattr(cd, "AsyncSessionLocal", sqlite_session)
    ml = _mk_coupon(coupon_code="MLC-OK", conditions="somente app")
    amz = _mk_coupon(provider="amazon", coupon_code="AMZ9")
    await _seed(
        sqlite_session,
        ml, _mk_cp(ml.id, title="Notebook Dell Inspiron 15"),
        amz, _mk_cp(amz.id, title="Notebook Dell Inspiron 15"),
    )
    results = await cd.find_similar_coupon_products("Notebook Dell gamer", limit=5)
    codes = {r["coupon_code"] for r in results}
    assert "MLC-OK" in codes
    assert "AMZ9" not in codes
    row = next(r for r in results if r["coupon_code"] == "MLC-OK")
    assert row["coupon_verified"] is True
    assert row["coupon_conditions"] == "somente app"


def test_fallback_raw_sql_scoped_to_mercadolivre():
    src = inspect.getsource(cd.select_coupon_offers)
    assert "c.provider = 'mercadolivre'" in src
    assert "c.conditions" in src


# ─── Catálogo: captions ──────────────────────────────────────────────────────

def _catalog_offer(coupon=None):
    offer = {
        "title": "Fone JBL Bluetooth",
        "provider": "mercadolivre",
        "final_price": 120.0,
        "original_price": 150.0,
        "discount_percent": 20.0,
        "affiliate_url": "https://meli.la/abc",
        "image_url": "https://img/x.jpg",
        "shipping_free": False,
        "economy": 30.0,
    }
    if coupon is not None:
        offer["coupon"] = coupon
    return offer


def test_catalog_caption_mlc_never_shows_code():
    coupon = {
        "verified": True, "code": "MLC-9", "discount_text": "10% OFF",
        "expires_at": FUTURE.isoformat(),
    }
    tg = distributor.build_caption_fallback(_catalog_offer(coupon), "https://x/r/1")
    assert "MLC-9" not in tg
    assert "ativação na conta" in tg
    assert "Confira elegibilidade" in tg

    fb = distributor.build_caption_facebook(_catalog_offer(coupon))
    assert "MLC-9" not in fb
    assert "extra no checkout" not in fb

    yt = distributor.build_youtube_description(_catalog_offer(coupon), "https://meli.la/abc", "https://x/r/1")
    assert "MLC-9" not in yt


def test_catalog_caption_unverified_coupon_silenced():
    coupon = {"verified": False, "code": "LOJA9", "expires_at": FUTURE.isoformat()}
    tg = distributor.build_caption_fallback(_catalog_offer(coupon), "https://x/r/1")
    assert "LOJA9" not in tg


def test_caption_facebook_instagram_cta_split():
    offer = _catalog_offer()
    fb = distributor.build_caption_facebook(offer, channel="facebook")
    assert "Link nos comentários" in fb
    assert "link do perfil" not in fb
    ig = distributor.build_caption_facebook(offer, channel="instagram")
    assert "Ofertas no link do perfil. Procure pelo nome do produto." in ig
    assert "Link nos comentários" not in ig


def test_youtube_description_profile_first_and_plain_shortlink():
    offer = _catalog_offer()
    desc = distributor.build_youtube_description(offer, "https://meli.la/abc", "https://site/r/ZZ")
    first = desc.splitlines()[0]
    assert first == "Ofertas no link do perfil: procure pelo nome do produto."
    assert "/ofertas?canal=youtube" in desc
    assert "https://site/r/ZZ" in desc
    assert "Compre aqui" not in desc


def test_video_script_has_no_clickable_description_cta():
    src = inspect.getsource(distributor.generate_offer_video)
    for bad in ("Link na descrição", "LINK NA DESCRIÇÃO", "CLICA NA DESCRIÇÃO",
                "Confira na descrição", "link tá na descrição", "link da descrição"):
        assert bad.lower() not in src.lower()
    assert "Abra o link do perfil e procure este produto." in src
    assert "OFERTAS NO LINK DO PERFIL" in src


# ─── Cupons: captions ────────────────────────────────────────────────────────

def _coupon_offer(**kw):
    offer = {
        "title": "Notebook Dell Inspiron",
        "price": 50.0,
        "image_url": "https://img/x.jpg",
        "product_url": "https://www.mercadolivre.com.br/p/MLB1",
        "ml_code": "MLB1",
        "coupon_code": "MLC-5",
        "coupon_discount": "R$ 80 OFF",
        "coupon_discount_percent": 0,
        "coupon_discount_value": 80.0,   # desconto fixo > preço: nunca pode gerar negativo
        "coupon_expires_at": FUTURE,
        "coupon_verified": True,
        "coupon_conditions": "mínimo R$ 100",
        "store_name": "LojaX",
    }
    offer.update(kw)
    return offer


def test_coupon_caption_fixed_discount_gt_price_never_negative():
    offer = _coupon_offer()
    for builder in (cd.build_coupon_caption_telegram, cd.build_coupon_caption_facebook):
        cap = builder(offer)
        assert "Preço consultado: R$ 50,00" in cap
        assert "R$ -" not in cap
        assert "Com cupom:" not in cap
        assert "Economia:" not in cap
        assert "Desconto anunciado: R$ 80 OFF" in cap
        assert "Condições: mínimo R$ 100" in cap
        assert "Confira elegibilidade" in cap


def test_coupon_caption_price_none_graceful():
    offer = _coupon_offer(price=None)
    cap = cd.build_coupon_caption_telegram(offer)
    assert "Preço consultado" not in cap
    assert "Desconto anunciado" in cap


def test_coupon_caption_mlc_not_shown():
    offer = _coupon_offer(coupon_code="MLC-SECRET")
    for builder in (cd.build_coupon_caption_telegram,
                    cd.build_coupon_caption_facebook,
                    cd.build_coupon_youtube_description):
        assert "MLC-SECRET" not in builder(offer)


def test_coupon_youtube_description_profile_cta_first():
    desc = cd.build_coupon_youtube_description(_coupon_offer())
    assert "/ofertas?canal=youtube" in desc
    assert "link do perfil" in desc
    # CTA de perfil vem antes de qualquer link de produto
    assert desc.index("link do perfil") < desc.index("mercadolivre.com.br/p/MLB1")


def test_coupon_from_offer_mapping():
    offer = _coupon_offer(coupon_expires_at=FUTURE)
    c = coupon_from_offer(offer)
    assert c["verified"] is True
    assert c["code"] == "MLC-5"
    assert c["discount_text"] == "R$ 80 OFF"
    assert c["conditions"] == "mínimo R$ 100"
    assert c["expires_at"] is FUTURE
    assert coupon_is_current(c) is True
    expired = coupon_from_offer(_coupon_offer(coupon_expires_at=PAST))
    assert coupon_is_current(expired) is False
    unverified = coupon_from_offer(_coupon_offer(coupon_verified=False))
    assert coupon_is_current(unverified) is False


# ─── Post guards: cupom inválido nunca chega a HTTP ─────────────────────────

@pytest.mark.asyncio
async def test_post_coupon_telegram_invalid_coupon_no_http(monkeypatch):
    called = []
    class GuardedClient:
        def __init__(self, *a, **k): called.append(1)
    monkeypatch.setattr(cd.httpx, "AsyncClient", GuardedClient)
    monkeypatch.setattr(cd, "BOT_TOKEN", "tok")
    monkeypatch.setattr(cd, "CHANNEL_ID", "ch")
    res = await cd.post_coupon_telegram(_coupon_offer(coupon_expires_at=PAST))
    assert res == {"ok": False, "error": "Cupom sem associação válida ou vencido"}
    assert not called


@pytest.mark.asyncio
async def test_post_coupon_facebook_invalid_coupon_no_db_no_http(monkeypatch):
    pages = AsyncMock()
    monkeypatch.setattr(cd, "_get_facebook_pages", pages)
    res = await cd.post_coupon_facebook(_coupon_offer(coupon_verified=False))
    assert res == {"ok": False, "error": "Cupom sem associação válida ou vencido"}
    pages.assert_not_called()


@pytest.mark.asyncio
async def test_post_coupon_youtube_invalid_coupon_no_http(monkeypatch):
    res = await cd.post_coupon_youtube(_coupon_offer(coupon_expires_at=PAST))
    assert res == {"ok": False, "error": "Cupom sem associação válida ou vencido"}


# ─── post_coupon_youtube: fluxo novo (mock upload) ──────────────────────────

@pytest.mark.asyncio
async def test_post_coupon_youtube_uses_generic_generator_and_clean_title(tmp_path, monkeypatch):
    offer = _coupon_offer(coupon_code="MLC-SECRET")

    acct = SimpleNamespace(
        is_active=True, access_token="tok", refresh_token="ref",
        token_expires_at=None,
    )
    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def execute(self, stmt):
            return SimpleNamespace(scalar=lambda: acct)
    monkeypatch.setattr(cd, "AsyncSessionLocal", lambda: FakeSession())

    video_file = tmp_path / "v.mp4"
    video_file.write_bytes(b"x" * 9000)
    gen = AsyncMock(return_value=str(video_file))
    monkeypatch.setattr(distributor, "generate_offer_video", gen)
    old_gen = AsyncMock()
    monkeypatch.setattr(cd, "generate_coupon_video", old_gen)
    monkeypatch.setattr(cd, "mark_coupon_posted", lambda code: None)

    upload = AsyncMock(return_value={"video_id": "v1", "video_url": "https://youtu.be/v1"})
    from app.integrations.youtube import youtube_client
    monkeypatch.setattr(youtube_client, "upload_video", upload)

    res = await cd.post_coupon_youtube(offer)

    assert res["ok"] is True
    old_gen.assert_not_called()
    gen.assert_awaited_once()
    vo, _path = gen.await_args.args[0], gen.await_args.args[1]
    narration = gen.await_args.kwargs["custom_narration"]
    assert vo["provider"] == "mercadolivre"
    assert vo["final_price"] == offer["price"]
    assert vo["original_price"] is None
    assert vo["discount_percent"] == 0
    assert narration == (
        f"{offer['title']}. Consulte as condições do cupom e o preço final na loja. "
        "Abra o link do perfil e procure este produto."
    )
    kwargs = upload.await_args.kwargs
    assert kwargs["title"] == "Oferta com cupom: " + offer["title"][:60] + " | BestPriceToday"
    assert "MLC-SECRET" not in kwargs["title"]
    assert "MLC-SECRET" not in kwargs["description"]
    assert "/ofertas?canal=youtube" in kwargs["description"]


# ─── Categorias e agendamentos inalterados ──────────────────────────────────

def test_schedules_and_categories_unchanged():
    assert distributor.POST_SCHEDULE == [(12, 1), (19, 2)]
    assert distributor.YOUTUBE_POST_SCHEDULE == [(12, 1), (19, 1)]
    assert cd.COUPON_POST_SCHEDULE == [(12, 1), (19, 1)]
    assert set(distributor.DEMAND_CATEGORIES) == {
        "audio", "wearables", "games", "periferico", "gadgets", "casa",
        "cozinha", "eletro", "esportes", "beleza", "automotivo", "informatica",
    }


# ─── /links/social ───────────────────────────────────────────────────────────

def _social_app(Session):
    from fastapi import FastAPI
    from app.api.v1.endpoints import links as links_module

    app = FastAPI()
    app.include_router(links_module.router, prefix="/api/v1")

    async def _db():
        async with Session() as s:
            yield s
    app.dependency_overrides[get_db] = _db
    return app


def _mk_link(code, source, days_ago=1, **kw) -> ShortLink:
    vals = dict(
        code=code,
        affiliate_url=f"https://loja.ex/{code}",
        product_title=f"Produto {code}",
        provider="mercadolivre",
        price=10.0,
        image_url="https://img.ex/i.jpg",
        source=source,
        created_at=NOW - timedelta(days=days_ago),
    )
    vals.update(kw)
    return ShortLink(**vals)


async def _seed_links(Session):
    links = [
        _mk_link("TGONE", "distributor_telegram", days_ago=0),
        _mk_link("TGTWO", "distributor_telegram_camp", days_ago=2),
        _mk_link("IGONE", "distributor_instagram", days_ago=1),
        _mk_link("YTONE", "distributor_youtube", days_ago=1),
        _mk_link("FBONE", "distributor_facebook", days_ago=1),
        _mk_link("CPONE", "coupon", days_ago=1),
        _mk_link("CYTONE", "coupon_youtube", days_ago=1),
        _mk_link("CTGONE", "coupon_telegram_camp", days_ago=1),
        _mk_link("CFONE", "coupon_facebook", days_ago=1),
        _mk_link("NOPRICE", "distributor_telegram", days_ago=1, price=0),
        _mk_link("NOIMG", "distributor_telegram", days_ago=1, image_url="http://insecure/x.jpg"),
        _mk_link("WEBONE", "web", days_ago=1),
        _mk_link("OLDONE", "distributor_telegram", days_ago=31),
        _mk_link("FUTONE", "distributor_telegram", days_ago=-1),
        _mk_link("DEADONE", "distributor_telegram", days_ago=1, is_dead=True),
        _mk_link("HTTPONE", "distributor_telegram", days_ago=1, affiliate_url="http://loja.ex/x"),
        _mk_link("NOTITLE", "distributor_telegram", days_ago=1, product_title=None),
    ]
    await _seed(Session, *links)


@pytest.mark.asyncio
async def test_social_endpoint_validation_and_filters(sqlite_session):
    await _seed_links(sqlite_session)
    app = _social_app(sqlite_session)
    from httpx import AsyncClient, ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        # canal inválido / limit inválido → 422
        assert (await client.get("/api/v1/links/social", params={"channel": "tiktok"})).status_code == 422
        assert (await client.get("/api/v1/links/social", params={"limit": 0})).status_code == 422
        assert (await client.get("/api/v1/links/social", params={"limit": 101})).status_code == 422

        r = await client.get("/api/v1/links/social")
        assert r.status_code == 200
        offers = r.json()["offers"]
        codes = {o["code"] for o in offers}
        assert {"TGONE", "TGTWO", "IGONE", "YTONE", "FBONE", "CPONE", "CYTONE",
                "CTGONE", "CFONE", "NOPRICE", "NOIMG"} <= codes
        assert codes.isdisjoint({"WEBONE", "OLDONE", "FUTONE", "DEADONE", "HTTPONE", "NOTITLE"})

        for o in offers:
            assert set(o) == {"code", "title", "provider", "price", "image_url",
                              "created_at", "source", "url"}
            assert o["url"].endswith(f"/r/{o['code']}")
            assert "affiliate_url" not in o and "clicks" not in o
        nop = next(o for o in offers if o["code"] == "NOPRICE")
        assert nop["price"] is None
        noi = next(o for o in offers if o["code"] == "NOIMG")
        assert noi["image_url"] is None
        # ordenação created_at desc
        assert offers[0]["code"] == "TGONE"

        r = await client.get("/api/v1/links/social", params={"channel": "telegram"})
        assert {o["code"] for o in r.json()["offers"]} == {
            "TGONE", "TGTWO", "NOPRICE", "NOIMG", "CPONE", "CTGONE"}

        r = await client.get("/api/v1/links/social", params={"channel": "youtube"})
        assert {o["code"] for o in r.json()["offers"]} == {"YTONE", "CPONE", "CYTONE"}

        r = await client.get("/api/v1/links/social", params={"channel": "facebook"})
        assert {o["code"] for o in r.json()["offers"]} == {"FBONE", "CPONE", "CFONE"}

        # Instagram nunca recebe cupom: nem legado 'coupon' nem prefixo coupon_*
        r = await client.get("/api/v1/links/social", params={"channel": "instagram"})
        assert {o["code"] for o in r.json()["offers"]} == {"IGONE"}

        r = await client.get("/api/v1/links/social", params={"limit": 2})
        assert len(r.json()["offers"]) == 2


@pytest.mark.asyncio
async def test_social_endpoint_is_read_only(sqlite_session):
    await _seed_links(sqlite_session)
    app = _social_app(sqlite_session)
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import func, select

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        r = await client.get("/api/v1/links/social")
        assert r.status_code == 200
    async with sqlite_session() as s:
        total = (await s.execute(select(func.count()).select_from(ShortLink))).scalar()
        clicks = (await s.execute(select(func.coalesce(func.sum(ShortLink.clicks), 0)))).scalar()
    assert total == 17
    assert clicks == 0


# ─── distribute_coupons: short link por canal ────────────────────────────────

@pytest.mark.asyncio
async def test_distribute_coupons_creates_link_per_channel(monkeypatch):
    offer = _coupon_offer()
    monkeypatch.setattr(cd, "COUPON_POST_SCHEDULE", [(datetime.now(cd.BR_TIMEZONE).hour, 1)])
    monkeypatch.setattr(cd, "_dedup", {})
    monkeypatch.setattr(cd, "_save_dedup", lambda: None)
    monkeypatch.setattr(cd, "select_coupon_offers", AsyncMock(return_value=[offer]))
    monkeypatch.setattr(cd, "already_posted_coupon", lambda code: False)

    calls = []
    async def fake_short_link(short_link_offer, source=None, campaign=None):
        calls.append(source)
        return f"https://x/r/{source}"
    monkeypatch.setattr(distributor, "create_short_link", fake_short_link)

    tg = AsyncMock(return_value={"ok": True})
    fb = AsyncMock(return_value={"ok": True})
    yt = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(cd, "post_coupon_telegram", tg)
    monkeypatch.setattr(cd, "post_coupon_facebook", fb)
    monkeypatch.setattr(cd, "post_coupon_youtube", yt)

    import asyncio as _aio
    await cd.distribute_coupons()
    await _aio.sleep(0)

    assert calls == ["coupon_telegram", "coupon_facebook", "coupon_youtube"]
    assert tg.await_args.args[0]["short_url"] == "https://x/r/coupon_telegram"
    assert fb.await_args.args[0]["short_url"] == "https://x/r/coupon_facebook"
    assert yt.await_args.args[0]["short_url"] == "https://x/r/coupon_youtube"
    # cópias por canal — a oferta original mantém o fallback product_url
    assert offer["short_url"] == offer["product_url"]
    assert tg.await_args.args[0] is not offer


@pytest.mark.asyncio
async def test_post_coupon_youtube_recoups_expired_during_generation(tmp_path, monkeypatch):
    offer = _coupon_offer()
    acct = SimpleNamespace(
        is_active=True, access_token="tok", refresh_token="ref",
        token_expires_at=None,
    )
    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def execute(self, stmt):
            return SimpleNamespace(scalar=lambda: acct)
    monkeypatch.setattr(cd, "AsyncSessionLocal", lambda: FakeSession())

    video_file = tmp_path / "v.mp4"
    video_file.write_bytes(b"x" * 9000)
    monkeypatch.setattr(distributor, "generate_offer_video", AsyncMock(return_value=str(video_file)))

    checks = iter([True, False])
    monkeypatch.setattr(cd, "coupon_is_current", lambda *a, **k: next(checks))
    upload = AsyncMock()
    from app.integrations.youtube import youtube_client
    monkeypatch.setattr(youtube_client, "upload_video", upload)

    res = await cd.post_coupon_youtube(offer)
    assert res == {"ok": False, "error": "Cupom sem associação válida ou vencido"}
    upload.assert_not_called()
    assert not video_file.exists()


# ─── Comentário do Instagram usa CTA de perfil ───────────────────────────────

@pytest.mark.asyncio
async def test_instagram_comment_uses_profile_cta(monkeypatch):
    acct = SimpleNamespace(instagram_id="ig1", access_token="tok")
    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def execute(self, stmt):
            return SimpleNamespace(scalar=lambda: acct)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", lambda: FakeSession())

    client = SimpleNamespace(
        publish_photo_instagram=AsyncMock(return_value={"media_id": "m1"}),
        post_comment_facebook=AsyncMock(return_value="c1"),
        pin_comment_facebook=AsyncMock(return_value=True),
    )
    from app.integrations import instagram as ig_module
    monkeypatch.setattr(ig_module, "InstagramFacebookClient", lambda: client)

    res = await distributor.post_to_instagram(_catalog_offer(), "cap", short_url="https://x/r/1")
    assert res["ok"] is True
    msg = client.post_comment_facebook.await_args.kwargs["message"]
    assert "Ofertas no link do perfil. Procure pelo nome do produto." in msg
    assert "Referência: https://x/r/1" in msg
    assert "Compre aqui" not in msg
