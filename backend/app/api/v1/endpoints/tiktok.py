from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.integrations.tiktok import tiktok_client
from app.core.config import settings
import uuid

router = APIRouter()

@router.get("/auth")
async def tiktok_auth():
    """Inicia o fluxo de autenticação do TikTok."""
    state = str(uuid.uuid4())
    # TODO: Salvar o state no Redis ou DB para validar no callback
    auth_url = tiktok_client.get_auth_url(state)
    return {"auth_url": auth_url}

@router.get("/callback")
async def tiktok_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Recebe o código do TikTok e troca pelo token."""
    try:
        token_data = await tiktok_client.get_access_token(code)
        # TODO: Salvar token_data no banco de dados vinculado ao usuário/admin
        return {
            "status": "success",
            "message": "TikTok autorizado com sucesso!",
            "data": token_data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na autorização: {str(e)}")

@router.post("/publish")
async def publish_to_tiktok(
    video_url: str,
    title: str,
    description: str,
    access_token: str, # TODO: Pegar do banco de dados
    db: AsyncSession = Depends(get_db)
):
    """Publica um vídeo no TikTok."""
    try:
        result = await tiktok_client.publish_video(access_token, video_url, title, description)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao publicar: {str(e)}")
