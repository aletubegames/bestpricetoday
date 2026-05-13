"""Favoritos — CRUD simples identificado por telegram_id (sem auth JWT)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.session import get_db
from app.models.models import Favorite, Product
from app.schemas.schemas import FavoriteCreate, FavoriteResponse
from uuid import UUID
import uuid

router = APIRouter()


@router.post("/favorites", response_model=FavoriteResponse)
async def add_favorite(
    body: FavoriteCreate,
    telegram_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Adiciona produto aos favoritos. telegram_id identifica o usuário anonimamente."""
    # Verifica se o produto existe
    result = await db.execute(select(Product).where(Product.id == body.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    obj = Favorite(
        id=uuid.uuid4(),
        user_id=None,
        product_id=body.product_id,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/favorites", response_model=list[FavoriteResponse])
async def list_favorites(
    telegram_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Favorite))
    return result.scalars().all()


@router.delete("/favorites/{favorite_id}")
async def remove_favorite(favorite_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Favorite).where(Favorite.id == favorite_id))
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(fav)
    return {"ok": True}
