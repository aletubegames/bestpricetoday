from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.schemas import AlertCreate, AlertResponse
from app.models.models import PriceAlert
from sqlalchemy import select
from uuid import UUID
import uuid

router = APIRouter()


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    """Cria alerta de preço. user_id é opcional — alertas anônimos identificados por telegram_id."""
    obj = PriceAlert(
        id=uuid.uuid4(),
        user_id=None,
        telegram_id=alert.telegram_id,
        query=alert.query,
        target_price=alert.target_price,
        product_id=alert.product_id,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    telegram_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista alertas. Filtra por telegram_id se fornecido."""
    stmt = select(PriceAlert).where(PriceAlert.is_active == True)
    if telegram_id:
        stmt = stmt.where(PriceAlert.telegram_id == telegram_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceAlert).where(PriceAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    return {"ok": True}
