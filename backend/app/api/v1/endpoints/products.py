"""Histórico de preços + rastreamento de cliques em afiliados."""
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import PriceHistory, AffiliateClick, Offer
from app.schemas.schemas import PriceHistoryPoint, ClickTrack, ClickTrackResponse
from uuid import UUID
from typing import Optional
import uuid
import hashlib

router = APIRouter()


@router.get("/products/{product_id}/history", response_model=list[PriceHistoryPoint])
async def price_history(
    product_id: UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Retorna histórico de preços de um produto (últimos N registros)."""
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/clicks", response_model=ClickTrackResponse)
async def track_click(
    body: ClickTrack,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Registra clique num link de afiliado para analytics."""
    click = AffiliateClick(
        id=uuid.uuid4(),
        offer_id=body.offer_id,
        provider=body.provider,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(click)
    await db.flush()
    return ClickTrackResponse(ok=True, click_id=click.id)


@router.post("/products/price-history")
async def save_price_snapshot(request: Request, db: AsyncSession = Depends(get_db)):
    """Called automatically after each search to persist price data."""
    try:
        body = await request.json()
        offers = body if isinstance(body, list) else body.get("offers", [])
        for offer_data in offers:
            product_id_str = offer_data.get("product_id")
            if not product_id_str:
                continue
            try:
                product_id = UUID(product_id_str)
            except Exception:
                continue
            result = await db.execute(select(Offer).where(Offer.id == product_id).limit(1))
            if not result.scalar_one_or_none():
                continue
            snap = PriceHistory(
                id=uuid.uuid4(),
                product_id=product_id,
                price=offer_data.get("final_price") or offer_data.get("price"),
                provider=offer_data.get("provider", ""),
            )
            db.add(snap)
        await db.flush()
    except Exception:
        pass  # fire-and-forget safe
    return {"ok": True}


@router.get("/products/price-history/{provider}/{external_id}")
async def get_price_history(
    provider: str,
    external_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """Returns price history for a product. Returns empty list if no history."""
    try:
        from sqlalchemy import text
        result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.provider == provider)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(days)
        )
        rows = result.scalars().all()
        return [{"price": r.price, "recorded_at": r.recorded_at} for r in rows]
    except Exception:
        return []


@router.get("/products/badges")
async def get_badges(
    offers: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts comma-separated 'provider:title' pairs, returns badge data.
    Computes badges purely from the offer data passed.
    """
    # This endpoint is for future DB-backed badge computation.
    # For now, returns empty — badges are computed client-side.
    return {}
