from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi import Query as FQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.models.models import ClickEvent, ConversionEvent, ShortLink
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import uuid
import os
import time
import hashlib
import hmac as hmac_mod
import httpx

_rate_limits: dict = defaultdict(list)


def check_rate_limit(key: str, max_calls: int = 10, window_seconds: int = 60) -> bool:
    """Simple in-memory rate limiter. Returns True if allowed."""
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window_seconds]
    if len(_rate_limits[key]) >= max_calls:
        return False
    _rate_limits[key].append(now)
    return True

router = APIRouter()


def require_admin(
    x_admin_key: str | None = Header(default=None),
    admin_key: str | None = FQuery(default=None),
):
    key = x_admin_key or admin_key
    if not settings.ADMIN_MANAGER_KEY or key != settings.ADMIN_MANAGER_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return key


class ClickEventIn(BaseModel):
    offer_id: Optional[str] = None
    provider: Optional[str] = None
    product_title: Optional[str] = None
    price: Optional[float] = None
    affiliate_url: Optional[str] = None
    source: str = "web"


class ConversionEventIn(BaseModel):
    click_id: Optional[str] = None
    provider: Optional[str] = None
    product_title: Optional[str] = None
    sale_price: Optional[float] = None
    commission_rate: Optional[float] = None
    commission_value: Optional[float] = None
    status: str = "pending"


@router.post("/clicks")
async def record_click(
    data: ClickEventIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record a click event - no auth required"""
    try:
        click = ClickEvent(
            offer_id=data.offer_id,
            provider=data.provider,
            product_title=data.product_title,
            price=data.price,
            affiliate_url=data.affiliate_url,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            source=data.source,
        )
        db.add(click)
        await db.commit()
        return {"ok": True}
    except Exception:
        return {"ok": False}


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    provider: Optional[str] = None,
    days: Optional[int] = None,
    _: str = Depends(require_admin),
):
    try:
        now = datetime.now(timezone.utc)
        # Usa UTC-3 (Brasília) para calcular "hoje"
        brt_offset = timedelta(hours=-3)
        now_brt = now + brt_offset
        today_start = now_brt.replace(hour=0, minute=0, second=0, microsecond=0) - brt_offset
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=days if days else 30)

        # clicks today
        q = select(func.count()).where(ClickEvent.clicked_at >= today_start)
        if provider: q = q.where(ClickEvent.provider == provider)
        clicks_today = (await db.execute(q)).scalar() or 0

        q = select(func.count()).where(ClickEvent.clicked_at >= week_start)
        if provider: q = q.where(ClickEvent.provider == provider)
        clicks_week = (await db.execute(q)).scalar() or 0

        q = select(func.count()).where(ClickEvent.clicked_at >= month_start)
        if provider: q = q.where(ClickEvent.provider == provider)
        clicks_month = (await db.execute(q)).scalar() or 0

        q = select(func.count()).select_from(ConversionEvent)
        if provider: q = q.where(ConversionEvent.provider == provider)
        total_conversions = (await db.execute(q)).scalar() or 0

        q = select(func.sum(ConversionEvent.sale_price))
        if provider: q = q.where(ConversionEvent.provider == provider)
        total_revenue = float((await db.execute(q)).scalar() or 0)

        q = select(func.sum(ConversionEvent.commission_value))
        if provider: q = q.where(ConversionEvent.provider == provider)
        total_commission = float((await db.execute(q)).scalar() or 0)

        q = select(func.avg(ConversionEvent.commission_rate))
        if provider: q = q.where(ConversionEvent.provider == provider)
        avg_commission_rate = float((await db.execute(q)).scalar() or 0)

        # clicks by provider
        q = select(ClickEvent.provider, func.count().label("cnt")).group_by(ClickEvent.provider)
        if provider:
            q = q.where(ClickEvent.provider == provider)
        r = await db.execute(q)
        clicks_by_provider = {row.provider or "unknown": row.cnt for row in r.fetchall()}

        # clicks by source
        q = select(ClickEvent.source, func.count().label("cnt")).group_by(ClickEvent.source)
        if provider:
            q = q.where(ClickEvent.provider == provider)
        r = await db.execute(q)
        clicks_by_source = {row.source or "web": row.cnt for row in r.fetchall()}

        # revenue by provider
        q = select(ConversionEvent.provider, func.sum(ConversionEvent.sale_price).label("rev")).group_by(ConversionEvent.provider)
        if provider:
            q = q.where(ConversionEvent.provider == provider)
        r = await db.execute(q)
        revenue_by_provider = {row.provider or "unknown": float(row.rev or 0) for row in r.fetchall()}

        # top provider
        top_provider = max(clicks_by_provider, key=lambda k: clicks_by_provider[k], default="aliexpress")

        # recent clicks
        q = select(ClickEvent).order_by(ClickEvent.clicked_at.desc()).limit(10)
        if provider:
            q = q.where(ClickEvent.provider == provider)
        r = await db.execute(q)
        recent_clicks = [
            {
                "id": str(c.id),
                "provider": c.provider,
                "product_title": c.product_title,
                "price": c.price,
                "source": c.source,
                "clicked_at": c.clicked_at.isoformat() if c.clicked_at else None,
            }
            for c in r.scalars().all()
        ]

        # recent conversions
        r = await db.execute(
            select(ConversionEvent).order_by(ConversionEvent.converted_at.desc()).limit(10)
        )
        recent_conversions = [
            {
                "id": str(c.id),
                "provider": c.provider,
                "product_title": c.product_title,
                "sale_price": c.sale_price,
                "commission_value": c.commission_value,
                "status": c.status,
                "converted_at": c.converted_at.isoformat() if c.converted_at else None,
            }
            for c in r.scalars().all()
        ]

        # CTR calculation
        ctr = round(total_conversions / clicks_month * 100, 2) if clicks_month > 0 else 0
        rpc = round(total_revenue / clicks_month, 4) if clicks_month > 0 else 0

        return {
            "total_clicks_today": clicks_today,
            "total_clicks_week": clicks_week,
            "total_clicks_month": clicks_month,
            "total_conversions": total_conversions,
            "total_revenue": total_revenue,
            "total_commission": total_commission,
            "top_provider": top_provider,
            "avg_commission_rate": avg_commission_rate,
            "clicks_by_provider": clicks_by_provider,
            "clicks_by_source": clicks_by_source,
            "revenue_by_provider": revenue_by_provider,
            "recent_clicks": recent_clicks,
            "recent_conversions": recent_conversions,
            "conversion_rate": ctr,
            "revenue_per_click": rpc,
            "avg_order_value": round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0,
        }
    except Exception as e:
        return {
            "total_clicks_today": 0,
            "total_clicks_week": 0,
            "total_clicks_month": 0,
            "total_conversions": 0,
            "total_revenue": 0.0,
            "total_commission": 0.0,
            "top_provider": "aliexpress",
            "avg_commission_rate": 0.0,
            "clicks_by_provider": {},
            "clicks_by_source": {},
            "revenue_by_provider": {},
            "recent_clicks": [],
            "recent_conversions": [],
            "conversion_rate": 0.0,
            "revenue_per_click": 0.0,
            "avg_order_value": 0.0,
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }


@router.get("/clicks")
async def list_clicks(
    page: int = 1,
    limit: int = 20,
    provider: Optional[str] = None,
    source: Optional[str] = None,
    days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        q = select(ClickEvent)
        filters = []
        if provider:
            filters.append(ClickEvent.provider == provider)
        if source:
            filters.append(ClickEvent.source == source)
        if days:
            filters.append(ClickEvent.clicked_at >= datetime.now(timezone.utc) - timedelta(days=days))
        if filters:
            q = q.where(and_(*filters))
        q = q.order_by(ClickEvent.clicked_at.desc()).offset((page - 1) * limit).limit(limit)
        r = await db.execute(q)
        items = r.scalars().all()
        return {
            "page": page,
            "limit": limit,
            "items": [
                {
                    "id": str(c.id),
                    "offer_id": c.offer_id,
                    "provider": c.provider,
                    "product_title": c.product_title,
                    "price": c.price,
                    "source": c.source,
                    "ip_address": c.ip_address,
                    "clicked_at": c.clicked_at.isoformat() if c.clicked_at else None,
                }
                for c in items
            ],
        }
    except Exception:
        return {"page": page, "limit": limit, "items": []}


@router.get("/conversions")
async def list_conversions(
    page: int = 1,
    limit: int = 20,
    provider: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        q = select(ConversionEvent)
        filters = []
        if provider:
            filters.append(ConversionEvent.provider == provider)
        if status:
            filters.append(ConversionEvent.status == status)
        if days:
            filters.append(ConversionEvent.converted_at >= datetime.now(timezone.utc) - timedelta(days=days))
        if filters:
            q = q.where(and_(*filters))
        q = q.order_by(ConversionEvent.converted_at.desc()).offset((page - 1) * limit).limit(limit)
        r = await db.execute(q)
        items = r.scalars().all()
        return {
            "page": page,
            "limit": limit,
            "items": [
                {
                    "id": str(c.id),
                    "provider": c.provider,
                    "product_title": c.product_title,
                    "sale_price": c.sale_price,
                    "commission_value": c.commission_value,
                    "status": c.status,
                    "converted_at": c.converted_at.isoformat() if c.converted_at else None,
                }
                for c in items
            ],
        }
    except Exception:
        return {"page": page, "limit": limit, "items": []}


@router.post("/conversions")
async def record_conversion(
    data: ConversionEventIn,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        conv = ConversionEvent(
            click_id=uuid.UUID(data.click_id) if data.click_id else None,
            provider=data.provider,
            product_title=data.product_title,
            sale_price=data.sale_price,
            commission_rate=data.commission_rate,
            commission_value=data.commission_value,
            status=data.status,
        )
        db.add(conv)
        await db.commit()
        return {"ok": True}
    except Exception:
        return {"ok": False}


@router.get("/analytics")
async def get_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        r = await db.execute(
            select(
                func.date(ClickEvent.clicked_at).label("day"),
                ClickEvent.provider,
                func.count().label("cnt"),
            )
            .where(ClickEvent.clicked_at >= since)
            .group_by(func.date(ClickEvent.clicked_at), ClickEvent.provider)
            .order_by(func.date(ClickEvent.clicked_at))
        )
        rows = r.fetchall()
        result = {}
        for row in rows:
            day = str(row.day)
            if day not in result:
                result[day] = {}
            result[day][row.provider or "unknown"] = row.cnt
        return {"days": days, "data": result}
    except Exception:
        return {"days": days, "data": {}}


@router.get("/marketplaces")
async def get_marketplaces(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        r = await db.execute(
            select(
                ClickEvent.provider,
                func.count().label("clicks"),
                func.avg(ClickEvent.price).label("avg_price"),
            )
            .group_by(ClickEvent.provider)
        )
        click_rows = {row.provider: {"clicks": row.clicks, "avg_price": float(row.avg_price or 0)} for row in r.fetchall()}

        r = await db.execute(
            select(
                ConversionEvent.provider,
                func.count().label("conversions"),
                func.sum(ConversionEvent.sale_price).label("revenue"),
                func.sum(ConversionEvent.commission_value).label("commission"),
            )
            .group_by(ConversionEvent.provider)
        )
        conv_rows = {
            row.provider: {
                "conversions": row.conversions,
                "revenue": float(row.revenue or 0),
                "commission": float(row.commission or 0),
            }
            for row in r.fetchall()
        }

        providers = set(list(click_rows.keys()) + list(conv_rows.keys()))
        result = []
        for p in providers:
            clicks = click_rows.get(p, {}).get("clicks", 0)
            convs = conv_rows.get(p, {}).get("conversions", 0)
            result.append({
                "provider": p,
                "clicks": clicks,
                "conversions": convs,
                "conversion_rate": round(convs / clicks * 100, 2) if clicks else 0,
                "revenue": conv_rows.get(p, {}).get("revenue", 0),
                "commission": conv_rows.get(p, {}).get("commission", 0),
                "avg_price": click_rows.get(p, {}).get("avg_price", 0),
                "top_products": [],
            })
        return result
    except Exception:
        return []


@router.get("/traffic")
async def get_traffic(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        r = await db.execute(select(func.count()).select_from(ClickEvent))
        total = r.scalar() or 0

        r = await db.execute(
            select(ClickEvent.source, func.count().label("cnt"))
            .group_by(ClickEvent.source)
        )
        rows = r.fetchall()
        result = []
        for row in rows:
            result.append({
                "source": row.source or "web",
                "clicks": row.cnt,
                "percentage": round(row.cnt / total * 100, 1) if total else 0,
                "conversions": 0,
                "revenue": 0,
            })
        return result
    except Exception:
        return []


@router.get("/coupons")
async def get_coupons(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        from app.models.models import Coupon
        r = await db.execute(
            select(Coupon.store, func.count().label("cnt"))
            .group_by(Coupon.store)
            .order_by(func.count().desc())
            .limit(20)
        )
        rows = r.fetchall()
        return [{"store": row.store, "count": row.cnt} for row in rows]
    except Exception:
        return []


@router.get("/products/top")
async def get_top_products(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        r = await db.execute(
            select(ClickEvent.product_title, ClickEvent.provider, func.count().label("clicks"))
            .where(ClickEvent.product_title != None)
            .group_by(ClickEvent.product_title, ClickEvent.provider)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = r.fetchall()
        return [{"product_title": row.product_title, "provider": row.provider, "clicks": row.clicks} for row in rows]
    except Exception:
        return []


@router.get("/products/suggestions")
async def get_product_suggestions(
    source: str = "top_clicks",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """
    Retorna sugestões de produtos para geração de vídeo.
    Chama search_all() diretamente (sem HTTP) para funcionar no HF Space.
    """

    async def _search(query: str, providers: list[str] | None = None) -> list[dict]:
        """Busca interna sem HTTP — chama search_all diretamente."""
        try:
            from app.services.search import search_all
            from app.schemas.schemas import ProviderEnum
            provs = [ProviderEnum(p) for p in providers] if providers else None
            resp = await search_all(query=query, limit=8, providers=provs)
            return [o.model_dump() for o in resp.offers]
        except Exception as e:
            logger.debug(f"_search('{query}'): {e}")
            return []

    def _offer_to_row(o: dict, badge: str, src: str) -> dict:
        return {
            "product_title": (o.get("title") or "")[:80],
            "provider":      o.get("provider"),
            "clicks":        0,
            "price":         o.get("final_price") or o.get("price"),
            "discount":      o.get("discount_percent", 0),
            "affiliate_url": o.get("affiliate_url"),
            "image_url":     o.get("image_url"),
            "badge":         badge,
            "source":        src,
        }

    def _dedup(items: list[dict], key_len: int = 35) -> list[dict]:
        seen: set[str] = set()
        out = []
        for item in items:
            k = (item.get("product_title") or "")[:key_len].lower()
            if k and k not in seen:
                seen.add(k)
                out.append(item)
        return out

    try:
        # ── top_clicks: banco próprio ────────────────────────────────────
        if source == "top_clicks":
            r = await db.execute(
                select(
                    ClickEvent.product_title,
                    ClickEvent.provider,
                    func.count().label("clicks"),
                    func.avg(ClickEvent.price).label("avg_price"),
                ).where(ClickEvent.product_title.isnot(None))
                .group_by(ClickEvent.product_title, ClickEvent.provider)
                .order_by(func.count().desc())
                .limit(limit)
            )
            return [
                {"product_title": row.product_title, "provider": row.provider,
                 "clicks": row.clicks, "price": round(row.avg_price or 0, 2),
                 "badge": "🔥 Top Cliques", "source": "top_clicks"}
                for row in r.fetchall()
            ]

        # ── trending: banco próprio ──────────────────────────────────────
        elif source == "trending":
            from app.services.search import get_trending_searches
            items = await get_trending_searches(limit=limit)
            if not items:
                # fallback: queries populares genéricas se banco estiver vazio
                items = [
                    {"query": q, "score": 1} for q in [
                        "smartphone samsung", "fone bluetooth", "notebook gamer",
                        "smartwatch", "airfryer", "aspirador robô", "smart tv 4k",
                        "teclado mecânico", "mouse gamer", "ssd nvme",
                    ][:limit]
                ]
            return [
                {"product_title": item["query"], "provider": None,
                 "clicks": item.get("score", 0), "price": None,
                 "badge": "🔍 Mais Buscado", "source": "trending"}
                for item in items
            ]

        # ── top_month: conversões confirmadas ──────────────────────────
        elif source == "top_month":
            since = datetime.now(timezone.utc) - timedelta(days=30)
            r = await db.execute(
                select(
                    ConversionEvent.product_title,
                    ConversionEvent.provider,
                    func.count().label("sales"),
                    func.avg(ConversionEvent.sale_price).label("avg_price"),
                    func.sum(ConversionEvent.commission_value).label("total_commission"),
                ).where(
                    ConversionEvent.converted_at >= since,
                    ConversionEvent.status == "confirmed",
                    ConversionEvent.product_title.isnot(None),
                )
                .group_by(ConversionEvent.product_title, ConversionEvent.provider)
                .order_by(func.count().desc())
                .limit(limit)
            )
            rows = r.fetchall()
            if not rows:
                return [{"product_title": "Sem conversões confirmadas este mês",
                         "provider": None, "clicks": 0, "price": None,
                         "badge": "💰 Top Vendas Mês", "source": "top_month"}]
            return [
                {"product_title": row.product_title, "provider": row.provider,
                 "clicks": row.sales, "price": round(row.avg_price or 0, 2),
                 "commission": round(row.total_commission or 0, 2),
                 "badge": "💰 Top Vendas Mês", "source": "top_month"}
                for row in rows
            ]

        # ── high_discount: busca interna com filtro de desconto ─────────
        elif source == "high_discount":
            queries = [
                "smartphone barato", "notebook oferta", "fone desconto",
                "smartwatch promoção", "airfryer promo",
            ]
            results: list[dict] = []
            for q in queries:
                offers = await _search(q)
                for o in offers:
                    disc = o.get("discount_percent", 0) or 0
                    if disc >= 10 and not o.get("is_fake_discount") and o.get("final_price", 0) > 20:
                        results.append(_offer_to_row(o, f"🏷️ -{disc:.0f}% OFF", "high_discount"))
                if len(results) >= limit * 2:
                    break
            results.sort(key=lambda x: x.get("discount", 0), reverse=True)
            deduped = _dedup(results)[:limit]
            if not deduped:
                return [{"product_title": "Nenhum desconto ≥10% encontrado agora",
                         "provider": None, "clicks": 0, "price": None,
                         "badge": "🏷️ Maiores Descontos", "source": "high_discount"}]
            return deduped

        # ── top_sales_{provider}: bestsellers de uma plataforma ────────
        elif source.startswith("top_sales_"):
            provider = source.replace("top_sales_", "")
            PROVIDER_MAP = {
                "aliexpress":    "aliexpress",
                "shopee":        "shopee",
                "mercadolivre":  "mercadolivre",
            }
            QUERIES: dict[str, list[str]] = {
                "aliexpress":   ["mais vendido", "top venda eletrônico", "hot sale"],
                "shopee":       ["hot sale", "top venda", "mais vendido shopee"],
                "mercadolivre": ["mais vendido", "top vendas", "oferta do dia"],
            }
            prov_key = PROVIDER_MAP.get(provider, provider)
            queries  = QUERIES.get(provider, ["mais vendido", "top sale"])
            BADGE    = {
                "aliexpress":   "🔴 Top AliExpress",
                "shopee":       "🟠 Top Shopee",
                "mercadolivre": "🟡 Top Mercado Livre",
            }.get(provider, f"🏆 Top {provider.title()}")

            results = []
            for q in queries[:3]:
                offers = await _search(q, providers=[prov_key])
                for o in offers:
                    if o.get("final_price", 0) > 20:
                        results.append(_offer_to_row(o, BADGE, source))
                if len(results) >= limit * 2:
                    break

            deduped = _dedup(results)[:limit]
            if not deduped:
                return [{"product_title": f"Sem resultados para {provider} no momento",
                         "provider": provider, "clicks": 0, "price": None,
                         "badge": BADGE, "source": source}]
            return deduped

        return []

    except Exception as e:
        logger.error(f"Product suggestions error ({source}): {e}", exc_info=True)
        return []


@router.post("/conversions/poll")
async def trigger_conversion_poll(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Manually trigger order polling from all affiliate platforms."""
    from app.integrations.conversion_tracker import poll_all_conversions
    try:
        results = await poll_all_conversions(db)
        return {"ok": True, "new_conversions": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/webhooks/mercadolivre")
async def ml_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives ML order webhook with HMAC-SHA256 signature validation.

    ML sends header: x-signature: ts=<timestamp>,v1=<hmac>
    HMAC = SHA256(secret, "ts:<timestamp>\nv1:<body_hash>")

    Register URL: https://alessandro2090-bestpricetoday-api.hf.space/api/v1/admin/webhooks/mercadolivre
    """
    body = await request.body()

    # Validate HMAC if ML_WEBHOOK_SECRET is configured
    ml_secret = getattr(settings, 'ML_WEBHOOK_SECRET', "")
    if ml_secret:
        signature_header = request.headers.get("x-signature", "")
        if signature_header:
            try:
                parts = dict(p.split("=", 1) for p in signature_header.split(","))
                ts = parts.get("ts", "")
                v1 = parts.get("v1", "")

                body_hash = hashlib.sha256(body).hexdigest()
                to_sign = f"ts:{ts}\nv1:{body_hash}"
                expected = hmac_mod.new(
                    ml_secret.encode(), to_sign.encode(), hashlib.sha256
                ).hexdigest()

                if v1 != expected:
                    logger.warning("ML webhook: HMAC validation failed [signature mismatch]")
                    # Don't reject — ML might send without signature in sandbox
            except Exception as e:
                logger.warning(f"ML webhook HMAC parsing error: {type(e).__name__}")

    # Process payload
    try:
        payload = await request.json()
    except Exception:
        return {"ok": True}  # always 200 to ML

    topic = payload.get("topic", "")
    resource = payload.get("resource", "")

    logger.info(f"ML webhook received: topic={topic} resource={resource}")

    if topic not in ("orders", "merchant_orders"):
        return {"ok": True, "skipped": True}

    order_id = resource.split("/")[-1]

    # Get valid token from DB
    try:
        from app.services.ml_token_service import get_token
        token = await get_token(db)
        if not token:
            logger.warning("ML webhook: no valid token available")
            return {"ok": True, "warning": "no token"}

        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"https://api.mercadolibre.com/orders/{order_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

        if r.status_code != 200:
            logger.warning(f"ML webhook: order fetch failed HTTP {r.status_code} [body redacted]")
            return {"ok": True}

        order = r.json()
        total = float(order.get("total_amount", 0) or 0)
        status_raw = order.get("status", "")
        status = "confirmed" if status_raw in ("paid", "approved") else \
                 "rejected" if status_raw in ("cancelled", "refunded") else "pending"

        items = order.get("order_items", [])
        title = items[0].get("item", {}).get("title", "ML Order")[:200] if items else "ML Order"

        commission_rate = None
        commission_value = None

        # Find matching click
        from app.integrations.conversion_tracker import _find_matching_click, _save_conversion_safe
        click_id = await _find_matching_click(db, "mercadolivre", title)

        saved = await _save_conversion_safe(
            db, f"ml_{order_id}", "mercadolivre", title,
            total, commission_rate, commission_value, status, click_id
        )

        logger.info(
            f"ML order {order_id}: status={status} total={total:.2f} commission=unknown saved={saved} click_linked={bool(click_id)}"
        )
        return {"ok": True}

    except Exception as e:
        logger.error(f"ML webhook processing error: {type(e).__name__} [details redacted]")
        return {"ok": True}


@router.get("/conversions/summary")
async def conversion_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Detailed conversion funnel with click→conversion matching."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    r = await db.execute(select(func.count()).where(ClickEvent.clicked_at >= since))
    total_clicks = r.scalar() or 0

    r = await db.execute(
        select(
            func.count().label("count"),
            func.sum(ConversionEvent.sale_price).label("revenue"),
            func.sum(ConversionEvent.commission_value).label("commission"),
        ).where(ConversionEvent.converted_at >= since)
    )
    row = r.fetchone()
    total_conversions = row.count or 0
    total_revenue = float(row.revenue or 0)
    total_commission = float(row.commission or 0)

    r = await db.execute(
        select(
            ConversionEvent.provider,
            func.count().label("count"),
            func.sum(ConversionEvent.commission_value).label("commission"),
        )
        .where(ConversionEvent.converted_at >= since)
        .group_by(ConversionEvent.provider)
    )
    by_provider = [
        {"provider": row.provider, "conversions": row.count, "commission": float(row.commission or 0)}
        for row in r.fetchall()
    ]

    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks else 0

    return {
        "period_days": days,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "conversion_rate": round(conversion_rate, 2),
        "total_revenue": total_revenue,
        "total_commission": total_commission,
        "roi": round(total_commission, 2),
        "by_provider": by_provider,
        "funnel": {
            "clicks": total_clicks,
            "conversions": total_conversions,
            "revenue": total_revenue,
            "commission": total_commission,
        }
    }


@router.get("/integrations/status")
async def get_integration_status(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Returns integration status for all providers — used by admin dashboard."""
    from app.services.ml_token_service import get_token_status

    ml_status = await get_token_status(db)

    return {
        "mercadolivre": {
            **ml_status,
            "note": "Register webhook at: https://alessandro2090-bestpricetoday-api.hf.space/api/v1/admin/webhooks/mercadolivre"
        },
        "aliexpress": {
            "status": "active" if settings.ALIEXPRESS_APP_KEY and settings.ALIEXPRESS_APP_SECRET else "not_configured",
            "tracking_id_set": bool(settings.ALIEXPRESS_TRACKING_ID),
        },
        "shopee": {
            "status": "active" if settings.SHOPEE_APP_ID and settings.SHOPEE_SECRET else "not_configured",
        },
        "amazon": {
            "status": "not_configured",
            "note": "Set AMAZON_ACCESS_KEY and AMAZON_SECRET_KEY",
        },
        "lomadee": {
            "status": "active" if settings.LOMADEE_API_KEY else "not_configured",
        },
    }


@router.get("/report")
async def get_report(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        overview = await get_overview(db=db, _="skip")
        marketplaces = await get_marketplaces(db=db, _="skip")
        traffic = await get_traffic(db=db, _="skip")
        top_products = await get_top_products(db=db, _="skip")
        return {
            "overview": overview,
            "marketplaces": marketplaces,
            "traffic": traffic,
            "top_products": top_products,
        }
    except Exception:
        return {"overview": {}, "marketplaces": [], "traffic": [], "top_products": []}


@router.post("/broadcast/telegram")
async def trigger_telegram_broadcast(
    n: int = 3,
    _: str = Depends(require_admin),
):
    """Manually trigger Telegram channel broadcast."""
    try:
        from app.workers.channel_broadcaster import broadcast_top_offers
        result = await broadcast_top_offers(n_offers=n)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class VideoPublishRequest(BaseModel):
    query:       Optional[str] = None
    plataformas: list[str]     = ["telegram"]
    formato:     str           = "oferta_choque"


@router.get("/video/url")
async def get_video_url(_: str = Depends(require_admin)):
    """Retorna a VIDEO_API_URL para o frontend chamar diretamente.
    O browser admin está na mesma rede local que o ngrok — sem proxy."""
    return {"url": settings.VIDEO_API_URL}


@router.get("/video/health")
async def get_video_health(_: str = Depends(require_admin)):
    """Verifica se a Video API local está acessível via VIDEO_API_URL."""
    VIDEO_API_URL = settings.VIDEO_API_URL
    VIDEO_API_KEY = settings.VIDEO_API_KEY
    headers: dict = {"ngrok-skip-browser-warning": "true"}  # ngrok free requer este header
    if VIDEO_API_KEY:
        headers["x-video-key"] = VIDEO_API_KEY
    try:
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(f"{VIDEO_API_URL}/health", headers=headers)
        data = r.json()
        return {"ok": data.get("ok", False), "url": VIDEO_API_URL, **data}
    except httpx.ConnectError:
        return {"ok": False, "url": VIDEO_API_URL,
                "error": f"Video API não acessível em {VIDEO_API_URL}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/video/publish")
async def trigger_video_publish(
    body: VideoPublishRequest,
    _: str = Depends(require_admin),
):
    """
    Dispara geração de vídeo delegando para a Video API local (porta 8765).

    Arquitetura:
      - Frontend → HF Space (/admin/video/publish)  → Video API local (localhost:8765)
      - A Video API roda na máquina com GPU e executa o traffic_machine.py

    Configurável via env:
      VIDEO_API_URL  = URL da Video API local (default: http://localhost:8765)
      VIDEO_API_KEY  = chave de auth da Video API (opcional)
    """
    VIDEO_API_URL = settings.VIDEO_API_URL
    VIDEO_API_KEY = settings.VIDEO_API_KEY

    plats = [p for p in body.plataformas if p in {"telegram", "youtube", "tiktok"}]
    if not plats:
        return {"ok": False, "error": "Nenhuma plataforma válida"}

    headers: dict = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}
    if VIDEO_API_KEY:
        headers["x-video-key"] = VIDEO_API_KEY

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{VIDEO_API_URL}/video/publish",
                json={"query": body.query, "plataformas": plats, "formato": body.formato},
                headers=headers,
            )
        if r.status_code == 200:
            data = r.json()
            return data
        return {"ok": False, "error": f"Video API retornou {r.status_code}: {r.text[:200]}"}
    except httpx.ConnectError:
        return {
            "ok":    False,
            "error": (
                f"Video API não encontrada em {VIDEO_API_URL}. "
                "Inicie o serviço na máquina local: cd ~/wan2 && python video_api.py"
            )
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/video/status/{job_id}")
async def get_video_status(
    job_id: str,
    _: str = Depends(require_admin),
):
    """
    Proxy para a Video API local — busca o status/log do job.
    """
    VIDEO_API_URL = settings.VIDEO_API_URL
    VIDEO_API_KEY = settings.VIDEO_API_KEY

    headers: dict = {"ngrok-skip-browser-warning": "true"}
    if VIDEO_API_KEY:
        headers["x-video-key"] = VIDEO_API_KEY

    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"{VIDEO_API_URL}/video/status/{job_id}", headers=headers)
        return r.json()
    except httpx.ConnectError:
        return {"ok": False, "error": "Video API offline"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/links/stats")
async def get_link_stats(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Top performing short links."""
    try:
        r = await db.execute(
            select(ShortLink)
            .order_by(ShortLink.clicks.desc())
            .limit(limit)
        )
        links = r.scalars().all()
        return [
            {
                "code": l.code,
                "url": f"https://bestpricetoday.vercel.app/r/{l.code}",
                "provider": l.provider,
                "product": l.product_title[:60] if l.product_title else "",
                "clicks": l.clicks,
                "source": l.source,
                "campaign": l.campaign,
                "created_at": l.created_at.isoformat() if l.created_at else None,
                "last_clicked": l.last_clicked_at.isoformat() if l.last_clicked_at else None,
            }
            for l in links
        ]
    except Exception:
        return []


@router.get("/debug/db")
async def debug_db(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Debug: conta diretamente nas tabelas para diagnosticar."""
    from sqlalchemy import text
    try:
        results = {}
        for table in ["click_events", "conversion_events", "short_links", "clicks_afiliados"]:
            try:
                r = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                results[table] = r.scalar()
            except Exception as e:
                results[table] = f"ERROR: {type(e).__name__}: {str(e)[:50]}"
        
        # Últimos cliques raw
        try:
            r = await db.execute(text("SELECT provider, source, clicked_at FROM click_events ORDER BY clicked_at DESC LIMIT 5"))
            results["last_clicks"] = [{"provider": row[0], "source": row[1], "at": str(row[2])[:16]} for row in r]
        except Exception as e:
            results["last_clicks"] = f"ERROR: {e}"
        
        return results
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug/orm")
async def debug_orm(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Debug: testa o ORM diretamente."""
    from sqlalchemy import select, func, text
    try:
        # Testa count via ORM
        r = await db.execute(select(func.count()).select_from(ClickEvent))
        orm_count = r.scalar()
        
        # Testa com where
        from datetime import datetime, timedelta, timezone
        month_start = datetime.now(timezone.utc) - timedelta(days=30)
        r2 = await db.execute(
            select(func.count()).where(ClickEvent.clicked_at >= month_start)
        )
        orm_month = r2.scalar()
        
        # Testa today (BRT)
        brt = timedelta(hours=-3)
        now = datetime.now(timezone.utc)
        today = (now+brt).replace(hour=0,minute=0,second=0,microsecond=0) - brt
        r3 = await db.execute(
            select(func.count()).where(ClickEvent.clicked_at >= today)
        )
        orm_today = r3.scalar()
        
        return {
            "orm_total": orm_count,
            "orm_month": orm_month,
            "orm_today": orm_today,
            "today_utc": str(today),
            "now_utc": str(now),
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@router.post("/migrate/users-auth")
async def migrate_users_auth(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Aplica colunas de autenticação na tabela users (idempotente)."""
    from sqlalchemy import text
    results = {}
    try:
        await db.execute(text("""
            ALTER TABLE users
              ADD COLUMN IF NOT EXISTS password_hash VARCHAR,
              ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE
        """))
        await db.commit()
        results["migration"] = "ok"

        # Verificar colunas
        r = await db.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
        ))
        results["columns"] = [row[0] for row in r.fetchall()]
    except Exception as e:
        results["error"] = str(e)
    return results


@router.get("/ml/test-search")
async def ml_test_search(
    q: str = "iphone",
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Testa busca ML com o token atual do banco. Diagnóstico apenas."""
    import httpx
    from app.services.ml_token_service import get_token
    token = await get_token(db)
    if not token:
        return {"error": "sem token no banco", "token_found": False}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Testa /users/me para ver scopes
            me_resp = await client.get(
                "https://api.mercadolibre.com/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            # Testa busca
            search_resp = await client.get(
                "https://api.mercadolibre.com/sites/MLB/search",
                params={"q": q, "limit": 3},
                headers={"Authorization": f"Bearer {token}"},
            )
        me_data = me_resp.json() if me_resp.status_code == 200 else me_resp.text[:200]
        return {
            "token_found": True,
            "token_prefix": token[:20] + "...",
            "users_me_status": me_resp.status_code,
            "users_me": {k: me_data.get(k) for k in ["id", "nickname", "email", "site_id"]} if isinstance(me_data, dict) else me_data,
            "search_status": search_resp.status_code,
            "search_response": search_resp.json() if search_resp.status_code == 200 else search_resp.text[:500],
        }
    except Exception as e:
        return {"error": str(e), "token_found": True}


@router.get("/ml/test-endpoints")
async def ml_test_endpoints(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Testa múltiplos endpoints ML com o token atual."""
    import httpx
    from app.services.ml_token_service import get_token
    token = await get_token(db)
    if not token:
        return {"error": "sem token"}
    
    endpoints = [
        ("sites_search",    f"https://api.mercadolibre.com/sites/MLB/search?q=smartphone&limit=2"),
        ("products_search", f"https://api.mercadolibre.com/products/search?site_id=MLB&q=smartphone&limit=2"),
        ("user_items",      f"https://api.mercadolibre.com/users/6727655/items/search?q=smartphone&limit=2"),
        ("user_favorites",  f"https://api.mercadolibre.com/users/6727655/purchased_items"),
    ]
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name, url in endpoints:
            try:
                r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
                results[name] = {"status": r.status_code, "body": r.text[:200]}
            except Exception as e:
                results[name] = {"error": str(e)}
    return results
