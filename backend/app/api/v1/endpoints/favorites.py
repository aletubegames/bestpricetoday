"""
favorites.py — CRUD de favoritos com ownership obrigatório.

owner_id é sempre obrigatório (mesmo modelo que alerts):
  - no browser: localStorage["bpt_anon_id"]
  - no Telegram bot: str(update.effective_user.id)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import Favorite, Product
from app.schemas.schemas import FavoriteCreate, FavoriteResponse
from uuid import UUID
import uuid

router = APIRouter()


@router.post("/favorites", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    body: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Adiciona produto aos favoritos.
    owner_id vem no body (obrigatório via schema).
    """
    result = await db.execute(select(Product).where(Product.id == body.product_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    # Evita duplicata para o mesmo owner
    existing = await db.execute(
        select(Favorite).where(
            Favorite.owner_id == body.owner_id,
            Favorite.product_id == body.product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in favorites")

    obj = Favorite(
        id=uuid.uuid4(),
        user_id=None,
        owner_id=body.owner_id,
        product_id=body.product_id,
    )
    db.add(obj)
    await db.flush()
    return obj


@router.get("/favorites", response_model=list[FavoriteResponse])
async def list_favorites(
    owner_id: str = Query(..., min_length=1, description="ID do dono dos favoritos"),
    db: AsyncSession = Depends(get_db),
):
    """
    Lista favoritos do owner.
    owner_id é obrigatório — nunca lista favoritos de outros usuários.
    """
    stmt = (
        select(Favorite)
        .where(Favorite.owner_id == owner_id)
        .order_by(Favorite.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/favorites/{favorite_id}", status_code=200)
async def remove_favorite(
    favorite_id: UUID,
    owner_id: str = Query(..., min_length=1, description="ID do dono do favorito"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove favorito.
    Valida ownership: 404 se não pertencer ao owner_id.
    """
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.owner_id == owner_id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(fav)
    return {"ok": True}
