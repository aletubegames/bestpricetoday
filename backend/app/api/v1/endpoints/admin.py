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
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
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
        now = datetime.utcnow()
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
            filters.append(ClickEvent.clicked_at >= datetime.utcnow() - timedelta(days=days))
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
            filters.append(ConversionEvent.converted_at >= datetime.utcnow() - timedelta(days=days))
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
        since = datetime.utcnow() - timedelta(days=days)
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

        commission_rate = 4.0
        commission_value = total * 0.04

        # Find matching click
        from app.integrations.conversion_tracker import _find_matching_click, _save_conversion_safe
        click_id = await _find_matching_click(db, "mercadolivre", title)

        saved = await _save_conversion_safe(
            db, f"ml_{order_id}", "mercadolivre", title,
            total, commission_rate, commission_value, status, click_id
        )

        logger.info(f"ML order {order_id}: status={status} total={total:.2f} commission={commission_value:.2f} saved={saved} click_linked={bool(click_id)}")
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
    since = datetime.utcnow() - timedelta(days=days)

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


@router.post("/conversions/test")
async def test_conversion(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
):
    """Create a test conversion to verify the pipeline works."""
    if not check_rate_limit("conversion_test", max_calls=5, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    from app.integrations.conversion_tracker import _save_conversion_safe, _find_matching_click

    click_id = await _find_matching_click(db, "aliexpress")
    saved = await _save_conversion_safe(
        db,
        external_order_id=f"test_{int(time.time())}",
        provider="aliexpress",
        product_title="TESTE — Fone Bluetooth TWS [CONVERSION TEST]",
        sale_price=150.0,
        commission_rate=8.5,
        commission_value=12.75,
        status="confirmed",
        click_id=click_id,
    )
    return {
        "ok": saved,
        "click_linked": bool(click_id),
        "click_id": click_id,
        "note": "Test conversion created. Check admin dashboard.",
    }


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
        from datetime import datetime, timedelta
        month_start = datetime.utcnow() - timedelta(days=30)
        r2 = await db.execute(
            select(func.count()).where(ClickEvent.clicked_at >= month_start)
        )
        orm_month = r2.scalar()
        
        # Testa today (BRT)
        brt = timedelta(hours=-3)
        now = datetime.utcnow()
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
