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
    obj = PriceAlert(
        id=uuid.uuid4(),
        user_id=None,  # TODO: auth
        query=alert.query,
        target_price=alert.target_price,
        product_id=alert.product_id,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceAlert).where(PriceAlert.is_active == True))
    return result.scalars().all()


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PriceAlert).where(PriceAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    return {"ok": True}
