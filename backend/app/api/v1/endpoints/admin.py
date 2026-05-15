from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi import Query as FQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.config import settings
from app.db.session import get_db
from app.models.models import ClickEvent, ConversionEvent
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid

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
    _: str = Depends(require_admin),
):
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)

        # clicks today
        r = await db.execute(select(func.count()).where(ClickEvent.clicked_at >= today_start))
        clicks_today = r.scalar() or 0

        r = await db.execute(select(func.count()).where(ClickEvent.clicked_at >= week_start))
        clicks_week = r.scalar() or 0

        r = await db.execute(select(func.count()).where(ClickEvent.clicked_at >= month_start))
        clicks_month = r.scalar() or 0

        r = await db.execute(select(func.count()).select_from(ConversionEvent))
        total_conversions = r.scalar() or 0

        r = await db.execute(select(func.sum(ConversionEvent.sale_price)))
        total_revenue = float(r.scalar() or 0)

        r = await db.execute(select(func.sum(ConversionEvent.commission_value)))
        total_commission = float(r.scalar() or 0)

        r = await db.execute(select(func.avg(ConversionEvent.commission_rate)))
        avg_commission_rate = float(r.scalar() or 0)

        # clicks by provider
        r = await db.execute(
            select(ClickEvent.provider, func.count().label("cnt"))
            .group_by(ClickEvent.provider)
        )
        clicks_by_provider = {row.provider or "unknown": row.cnt for row in r.fetchall()}

        # clicks by source
        r = await db.execute(
            select(ClickEvent.source, func.count().label("cnt"))
            .group_by(ClickEvent.source)
        )
        clicks_by_source = {row.source or "web": row.cnt for row in r.fetchall()}

        # revenue by provider
        r = await db.execute(
            select(ConversionEvent.provider, func.sum(ConversionEvent.sale_price).label("rev"))
            .group_by(ConversionEvent.provider)
        )
        revenue_by_provider = {row.provider or "unknown": float(row.rev or 0) for row in r.fetchall()}

        # top provider
        top_provider = max(clicks_by_provider, key=lambda k: clicks_by_provider[k], default="aliexpress")

        # recent clicks
        r = await db.execute(
            select(ClickEvent).order_by(ClickEvent.clicked_at.desc()).limit(10)
        )
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
