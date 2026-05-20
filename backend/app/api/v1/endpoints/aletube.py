"""
AleTubeGames — Admin video upload, analysis, and publishing.
- Upload local vídeos (Linux)
- Extrai frames, gera análise IA (title, description, hashtags)
- Publica em TikTok + YouTube reutilizando código existente
- Rastreia cliques/conversões via short links
"""

import os
import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import AdminVideo, ShortLink
from app.core.config import settings
from app.api.v1.endpoints.admin import require_admin
from app.integrations.tiktok import TikTokClient

router = APIRouter(prefix="/aletube", tags=["aletube"])
tiktok_client = TikTokClient()

# Diretório de armazenamento
VIDEOS_DIR = "/tmp/aletube_videos"
os.makedirs(VIDEOS_DIR, exist_ok=True)


def _generate_code(length: int = 8) -> str:
    """Gera código único para short link."""
    return uuid.uuid4().hex[:length].upper()


async def _analyze_video(video_path: str, filename: str) -> dict:
    """
    Análise IA rápida do vídeo.
    Por enquanto, retorna placeholder com metadados básicos.
    Integração com Claude Vision pode ser feita depois.
    """
    try:
        # Placeholder: gera metadata básica
        title = f"AleTube Games - {filename.replace('.mp4', '')}"
        description = f"Novo vídeo do AleTube Games. Confira o produto!"
        hashtags = ["#aletubegames", "#tech", "#promo", "#shorts"]
        
        return {
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "duration_seconds": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na análise: {str(e)}")


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload de vídeo local.
    Retorna video_id para próximo passo (análise).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")
    
    # Salva arquivo
    file_ext = file.filename.split(".")[-1]
    if file_ext.lower() not in ["mp4", "mov", "avi", "mkv"]:
        raise HTTPException(status_code=400, detail="Formato não suportado (mp4, mov, avi, mkv)")
    
    file_id = uuid.uuid4().hex
    file_path = f"{VIDEOS_DIR}/{file_id}.{file_ext}"
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_size = len(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")
    
    # Cria registro no DB
    video = AdminVideo(
        id=uuid.uuid4(),
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        plataformas=["tiktok", "youtube"],  # padrão
        publish_status="pending",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    
    return {
        "video_id": str(video.id),
        "filename": file.filename,
        "file_size_bytes": file_size,
        "status": "ready_for_analysis",
    }


@router.post("/analyze")
async def analyze_video(
    video_id: str = Form(...),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Análise IA — extrai metadata do vídeo."""
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    
    if not os.path.exists(video.file_path):
        raise HTTPException(status_code=400, detail="Arquivo de vídeo não encontrado")
    
    # Análise
    analysis = await _analyze_video(video.file_path, video.filename)
    
    # Atualiza DB
    video.title = analysis["title"]
    video.description = analysis["description"]
    video.hashtags = analysis["hashtags"]
    video.duration_seconds = analysis["duration_seconds"]
    await db.commit()
    await db.refresh(video)
    
    return {
        "video_id": str(video.id),
        "title": video.title,
        "description": video.description,
        "hashtags": video.hashtags,
        "duration_seconds": video.duration_seconds,
    }


@router.post("/publish")
async def publish_video(
    video_id: str = Form(...),
    plataformas: Optional[str] = Form(default="tiktok,youtube"),
    affiliate_url: Optional[str] = Form(default=None),
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Publica vídeo em TikTok + YouTube.
    Cria short links rastreados para ambas plataformas.
    """
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    
    if not video.title or not video.description:
        raise HTTPException(status_code=400, detail="Vídeo não foi analisado ainda. Execute /analyze primeiro.")
    
    # Parse plataformas
    plats = [p.strip() for p in plataformas.split(",") if p.strip()]
    plats = [p for p in plats if p in ["tiktok", "youtube", "telegram"]]
    if not plats:
        raise HTTPException(status_code=400, detail="Nenhuma plataforma válida")
    
    video.plataformas = plats
    video.publish_status = "publishing"
    
    try:
        # TikTok Publishing
        if "tiktok" in plats:
            # Busca conta admin do TikTok
            from app.models.models import TikTokAccount
            result_tiktok = await db.execute(
                select(TikTokAccount).where(
                    TikTokAccount.account_type == "admin",
                    TikTokAccount.is_active == True
                )
            )
            tiktok_account = result_tiktok.scalar()
            if not tiktok_account:
                raise HTTPException(status_code=400, detail="Conta TikTok admin não conectada")
            
            # Publica via TikTok Content Posting API
            tiktok_result = await tiktok_client.admin_publish_video(
                access_token=tiktok_account.access_token,
                video_path=video.file_path,
                title=video.title,
                description=f"{video.description}\n\n{' '.join(video.hashtags or [])}"
            )
            
            if tiktok_result.get("video_id"):
                video.tiktok_video_id = tiktok_result["video_id"]
                
                # Cria short link para TikTok
                code_tiktok = None
                for _ in range(10):
                    candidate = _generate_code(8)
                    existing = await db.execute(select(ShortLink).where(ShortLink.code == candidate))
                    if not existing.scalar():
                        code_tiktok = candidate
                        break
                
                if code_tiktok and affiliate_url:
                    short_link_tiktok = f"https://bestpricetoday.vercel.app/r/{code_tiktok}"
                    link = ShortLink(
                        code=code_tiktok,
                        affiliate_url=affiliate_url,
                        provider="aletube",
                        product_title=video.title[:200],
                        source="aletube_admin",
                        campaign=f"video_{video.id}",
                    )
                    db.add(link)
                    video.tiktok_short_link = short_link_tiktok
        
        # YouTube Publishing via Video API
        if "youtube" in plats:
            VIDEO_API_URL = settings.VIDEO_API_URL
            VIDEO_API_KEY = settings.VIDEO_API_KEY
            
            headers = {"Content-Type": "application/json"}
            if VIDEO_API_KEY:
                headers["x-video-key"] = VIDEO_API_KEY
            
            async with httpx.AsyncClient(timeout=30) as client:
                yt_result = await client.post(
                    f"{VIDEO_API_URL}/video/publish",
                    json={
                        "file_path": video.file_path,
                        "title": video.title,
                        "description": video.description,
                        "tags": video.hashtags or [],
                        "plataformas": ["youtube"],
                    },
                    headers=headers,
                )
            
            if yt_result.status_code == 200:
                yt_data = yt_result.json()
                if yt_data.get("video_id"):
                    video.youtube_video_id = yt_data["video_id"]
                    
                    # Cria short link para YouTube
                    code_yt = None
                    for _ in range(10):
                        candidate = _generate_code(8)
                        existing = await db.execute(select(ShortLink).where(ShortLink.code == candidate))
                        if not existing.scalar():
                            code_yt = candidate
                            break
                    
                    if code_yt and affiliate_url:
                        short_link_yt = f"https://bestpricetoday.vercel.app/r/{code_yt}"
                        link = ShortLink(
                            code=code_yt,
                            affiliate_url=affiliate_url,
                            provider="aletube",
                            product_title=video.title[:200],
                            source="aletube_admin",
                            campaign=f"video_yt_{video.id}",
                        )
                        db.add(link)
                        video.youtube_short_link = short_link_yt
        
        video.publish_status = "published"
        video.published_at = datetime.now(timezone.utc)
        
    except Exception as e:
        video.publish_status = "failed"
        video.publish_error = str(e)
    
    await db.commit()
    await db.refresh(video)
    
    return {
        "video_id": str(video.id),
        "status": video.publish_status,
        "tiktok_video_id": video.tiktok_video_id,
        "youtube_video_id": video.youtube_video_id,
        "tiktok_short_link": video.tiktok_short_link,
        "youtube_short_link": video.youtube_short_link,
        "error": video.publish_error,
    }


@router.get("/videos")
async def list_videos(
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os vídeos publicados com stats."""
    result = await db.execute(select(AdminVideo).order_by(AdminVideo.created_at.desc()))
    videos = result.scalars().all()
    
    return {
        "total": len(videos),
        "videos": [
            {
                "id": str(v.id),
                "filename": v.filename,
                "title": v.title,
                "status": v.publish_status,
                "tiktok_video_id": v.tiktok_video_id,
                "youtube_video_id": v.youtube_video_id,
                "tiktok_views": v.tiktok_views,
                "youtube_views": v.youtube_views,
                "clicks_total": v.clicks_total,
                "conversions": v.conversions,
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v in videos
        ],
    }
