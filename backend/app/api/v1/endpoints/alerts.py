"""
alerts.py — CRUD de alertas de preço com ownership obrigatório.

owner_id é sempre obrigatório:
  - no browser: valor de localStorage["bpt_anon_id"] enviado pelo frontend
  - no Telegram bot: str(update.effective_user.id)

Isso garante que list e delete são sempre scoped ao dono,
sem risco de expor ou deletar alertas de outros usuários.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.schemas import AlertCreate, AlertResponse
from app.models.models import PriceAlert
from uuid import UUID
import uuid

router = APIRouter()


@router.post("/alerts", response_model=AlertResponse, status_code=201)
async def create_alert(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    """
    Cria alerta de preço.
    owner_id é obrigatório — garante que o alerta sempre tem um dono.
    """
    obj = PriceAlert(
        id=uuid.uuid4(),
        user_id=None,
        owner_id=alert.owner_id,
        query=alert.query,
        target_price=alert.target_price,
        product_id=alert.product_id,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    owner_id: str = Query(..., min_length=1, description="ID do dono do alerta"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista alertas ativos do owner.
    owner_id é obrigatório — nunca retorna alertas de outros usuários.
    """
    stmt = (
        select(PriceAlert)
        .where(PriceAlert.owner_id == owner_id, PriceAlert.is_active == True)
        .order_by(PriceAlert.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/alerts/{alert_id}", status_code=200)
async def delete_alert(
    alert_id: UUID,
    owner_id: str = Query(..., min_length=1, description="ID do dono do alerta"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove (desativa) alerta.
    Valida ownership: retorna 404 se alert_id não pertencer ao owner_id.
    Isso evita que um usuário delete alertas de outro apenas por adivinhar o UUID.
    """
    result = await db.execute(
        select(PriceAlert).where(
            PriceAlert.id == alert_id,
            PriceAlert.owner_id == owner_id,
            PriceAlert.is_active == True,
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False
    await db.flush()
    return {"ok": True}
