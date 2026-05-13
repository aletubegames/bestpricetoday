"""Histórico de preços + rastreamento de cliques em afiliados."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import PriceHistory, AffiliateClick, Offer
from app.schemas.schemas import PriceHistoryPoint, ClickTrack, ClickTrackResponse
from uuid import UUID
import uuid

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
