"""
AleTubeGames — Upload, análise IA e publicação multi-plataforma.

Fluxo:
  POST /aletube/upload            → recebe vídeo, salva, cria AdminVideo
  POST /aletube/analyze           → extrai metadata + gera conteúdo por plataforma via Claude
  POST /aletube/publish           → publica nas plataformas selecionadas
  GET  /aletube/videos            → lista vídeos publicados com stats
  GET  /aletube/accounts/status   → status de conexão de todas as plataformas
  GET  /aletube/auth/youtube      → inicia OAuth YouTube
  GET  /aletube/auth/facebook     → inicia OAuth Facebook/Instagram
  GET  /aletube/callback/youtube  → callback OAuth YouTube
  GET  /aletube/callback/facebook → callback OAuth Facebook/Instagram
  DELETE /aletube/accounts/{platform} → desconectar conta
"""

import os
import uuid
import json
import asyncio
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.db.session import get_db
from app.models.models import AdminVideo, ShortLink, TikTokAccount, YouTubeAccount, InstagramAccount, FacebookAccount
from app.core.config import settings
from app.api.v1.endpoints.admin import require_admin
from app.integrations.tiktok import tiktok_client
from app.integrations.youtube import youtube_client
from app.integrations.instagram import ig_fb_client

router = APIRouter(prefix="/aletube", tags=["aletube"])

log = logging.getLogger("aletube")

VIDEOS_DIR = os.environ.get("ALETUBE_VIDEOS_DIR", "/app/videos")  # ✅ Usar /app/videos (persistente no HF Space)
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Get INTERNAL_API_URL for serving videos publicly
INTERNAL_API_URL = os.environ.get("INTERNAL_API_URL", "http://localhost:8000")


def _generate_code(length: int = 8) -> str:
    return uuid.uuid4().hex[:length].upper()


def _get_public_video_url(video_id: str) -> str:
    """Convert local video path to public URL."""
    return f"{INTERNAL_API_URL}/aletube/serve/{video_id}"


# ─── Análise IA via Claude ────────────────────────────────────────────────────

async def _extract_video_metadata(file_path: str) -> dict:
    """Extrai duração, resolução e fps com ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-show_format", file_path
            ],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"duration_seconds": 0, "width": 0, "height": 0, "fps": 0}
        data = json.loads(result.stdout)
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"), {}
        )
        duration = float(data.get("format", {}).get("duration", 0))
        width    = int(video_stream.get("width", 0))
        height   = int(video_stream.get("height", 0))
        fps_str  = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            fps = round(int(num) / int(den), 2) if int(den) > 0 else 0
        except Exception:
            fps = 0
        return {"duration_seconds": int(duration), "width": width, "height": height, "fps": fps}
    except Exception:
        return {"duration_seconds": 0, "width": 0, "height": 0, "fps": 0}


async def _generate_platform_content(filename: str, duration_seconds: int, width: int, height: int) -> dict:
    """
    Usa Claude para gerar título, descrição, hashtags e bio por plataforma.
    Retorna dict com chaves: tiktok, youtube, instagram, facebook.
    Fallback para placeholder se ANTHROPIC_API_KEY não configurado.
    """
    if not settings.ANTHROPIC_API_KEY:
        # Fallback sem IA
        base_title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        return {
            "tiktok": {
                "title":       f"{base_title[:100]}",
                "description": f"🔥 {base_title}\n\n📲 Siga para mais conteúdo!\n\n",
                "hashtags":    ["#aletubegames", "#tech", "#promo", "#shorts", "#fyp"],
                "bio_note":    "Link na bio para ofertas 🛒",
            },
            "youtube": {
                "title":       f"{base_title[:100]} | AleTubeGames",
                "description": (
                    f"{base_title}\n\n"
                    "📌 Inscreva-se no canal para mais vídeos!\n\n"
                    "🛒 Acesse as melhores ofertas:\n"
                    "https://bestpricetoday.vercel.app\n\n"
                    "#AleTubeGames #Tech #Promo"
                ),
                "hashtags":    ["AleTubeGames", "Tech", "Promo", "Games", "Oferta", "Desconto"],
                "end_screen_note": "Adicione end screen com inscrição",
            },
            "instagram": {
                "title":       base_title[:100],
                "description": (
                    f"🎮 {base_title}\n\n"
                    "🔥 Oferta incrível! Link na bio ⬆️\n\n"
                    "#aletubegames #tech #games #promo #reel"
                ),
                "hashtags":    ["aletubegames", "tech", "games", "promo", "reel", "instagram", "viral"],
                "bio_note":    "Atualize o link na bio antes de postar",
            },
            "facebook": {
                "title":       base_title[:255],
                "description": (
                    f"🔥 {base_title}\n\n"
                    "Confira essa oferta incrível! Acesse o link nos comentários ou na bio.\n\n"
                    "👉 bestpricetoday.vercel.app"
                ),
                "hashtags":    ["AleTubeGames", "Promo", "Tech"],
                "bio_note":    "Fixe o link nos comentários",
            },
        }

    # Claude via API direta
    prompt = f"""Você é um especialista em marketing de conteúdo para redes sociais.

Vídeo: "{filename}"
Duração: {duration_seconds}s
Resolução: {width}x{height}px

Gere conteúdo otimizado para cada plataforma. Responda SOMENTE com JSON válido, sem markdown, sem explicações.

Formato:
{{
  "tiktok": {{
    "title": "título até 150 chars, chamativo, emoji no início",
    "description": "descrição até 200 chars, call to action, link no final quando possível",
    "hashtags": ["lista", "de", "3a5", "hashtags", "relevantes"],
    "bio_note": "instrução curta para o que colocar na bio"
  }},
  "youtube": {{
    "title": "título até 100 chars, keyword no início, sem clickbait excessivo",
    "description": "descrição até 500 chars, paragrafada, com link bestpricetoday.vercel.app, SEO",
    "hashtags": ["lista", "de", "10a15", "hashtags", "mix", "broad", "e", "nicho"],
    "end_screen_note": "sugestão de end screen / cards"
  }},
  "instagram": {{
    "title": "título curto para referência interna",
    "description": "caption até 300 chars, emojis, call to action, link na bio mencionado",
    "hashtags": ["lista", "de", "20a30", "hashtags", "agressivos"],
    "bio_note": "instrução para link na bio"
  }},
  "facebook": {{
    "title": "título até 255 chars",
    "description": "texto para o post, mais longo, menos hashtags, mais conversacional",
    "hashtags": ["3a5", "hashtags"],
    "bio_note": "instrução extra (fixar comentário, etc)"
  }}
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-3-haiku-20240307",
                    "max_tokens": 1500,
                    "messages":   [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            text = r.json()["content"][0]["text"].strip()
            # Remove markdown se vier
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
    except Exception:
        return {
            "tiktok":    {"title": filename, "description": "", "hashtags": [], "bio_note": ""},
            "youtube":   {"title": filename, "description": "", "hashtags": [], "end_screen_note": ""},
            "instagram": {"title": filename, "description": "", "hashtags": [], "bio_note": ""},
            "facebook":  {"title": filename, "description": "", "hashtags": [], "bio_note": ""},
        }


# ─── Accounts Status ─────────────────────────────────────────────────────────

@router.get("/accounts/status")
async def accounts_status(
    _:  str           = Depends(require_admin),
    db: AsyncSession  = Depends(get_db),
):
    """Retorna status de conexão de todas as plataformas."""
    # TikTok
    tt = (await db.execute(
        select(TikTokAccount).where(TikTokAccount.account_type == "admin", TikTokAccount.is_active == True)
    )).scalar()

    # YouTube
    yt = (await db.execute(
        select(YouTubeAccount).where(YouTubeAccount.is_active == True)
    )).scalar()

    # Instagram
    ig = (await db.execute(
        select(InstagramAccount).where(InstagramAccount.is_active == True)
    )).scalar()

    # Facebook
    fb = (await db.execute(
        select(FacebookAccount).where(FacebookAccount.is_active == True)
    )).scalar()

    now = datetime.now(timezone.utc)

    def _token_status(expires_at):
        if not expires_at:
            return "unknown"
        if expires_at < now:
            return "expired"
        if expires_at < now + timedelta(days=7):
            return "expiring_soon"
        return "ok"

    return {
        "tiktok": {
            "connected":     bool(tt),
            "display_name":  tt.display_name if tt else None,
            "avatar_url":    tt.avatar_url if tt else None,
            "token_status":  _token_status(tt.token_expires_at) if tt else None,
            "auth_url":      "/api/v1/tiktok/auth/admin",
        },
        "youtube": {
            "connected":     bool(yt),
            "channel_title": yt.channel_title if yt else None,
            "channel_url":   yt.channel_url if yt else None,
            "token_status":  _token_status(yt.token_expires_at) if yt else None,
            "auth_url":      "/api/v1/aletube/auth/youtube",
        },
        "instagram": {
            "connected":  bool(ig),
            "username":   ig.username if ig else None,
            "avatar_url": ig.avatar_url if ig else None,
            "token_status": _token_status(ig.token_expires_at) if ig else None,
            "auth_url":   "/api/v1/aletube/auth/facebook",
            "note":       "Conecta via Facebook Login (requer conta Business/Creator)",
        },
        "facebook": {
            "connected":  bool(fb),
            "page_name":  fb.page_name if fb else None,
            "page_url":   fb.page_url if fb else None,
            "token_status": _token_status(fb.token_expires_at) if fb else None,
            "auth_url":   "/api/v1/aletube/auth/facebook",
        },
    }


# ─── OAuth YouTube ────────────────────────────────────────────────────────────

@router.get("/auth/youtube")
async def auth_youtube():
    """Inicia OAuth flow YouTube (sem autenticação admin — seguro por design OAuth)."""
    import secrets as _sec
    state    = _sec.token_hex(16)
    auth_url = youtube_client.get_auth_url(state)
    if not settings.YOUTUBE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="YOUTUBE_CLIENT_ID não configurado")
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/youtube")
async def callback_youtube(
    code:  str,
    state: str,
    db:    AsyncSession  = Depends(get_db),
):
    try:
        token_data = await youtube_client.get_access_token(code)
        access_token  = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in    = token_data.get("expires_in", 3600)

        channel_info = await youtube_client.get_channel_info(access_token)

        existing = (await db.execute(
            select(YouTubeAccount).where(YouTubeAccount.channel_id == channel_info["channel_id"])
        )).scalar()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        if existing:
            existing.access_token     = access_token
            existing.refresh_token    = refresh_token or existing.refresh_token
            existing.token_expires_at = expires_at
            existing.channel_title    = channel_info.get("channel_title")
            existing.channel_url      = channel_info.get("channel_url")
            existing.thumbnail_url    = channel_info.get("thumbnail_url")
            existing.is_active        = True
        else:
            db.add(YouTubeAccount(
                channel_id    = channel_info["channel_id"],
                channel_title = channel_info.get("channel_title"),
                channel_url   = channel_info.get("channel_url"),
                thumbnail_url = channel_info.get("thumbnail_url"),
                access_token  = access_token,
                refresh_token = refresh_token,
                token_expires_at = expires_at,
            ))

        await db.commit()
        return {"status": "success", "channel_title": channel_info.get("channel_title")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro OAuth YouTube: {str(e)}")


# ─── OAuth Facebook / Instagram ───────────────────────────────────────────────

@router.get("/auth/facebook")
async def auth_facebook():
    """Inicia OAuth flow Facebook/Instagram (sem autenticação admin — seguro por design OAuth)."""
    import secrets as _sec
    state    = _sec.token_hex(16)
    auth_url = ig_fb_client.get_auth_url(state)
    if not settings.INSTAGRAM_APP_ID:
        raise HTTPException(status_code=400, detail="INSTAGRAM_APP_ID não configurado")
    return {"auth_url": auth_url, "state": state}


@router.get("/callback/facebook")
async def callback_facebook(
    code:  str,
    state: str,
    db:    AsyncSession  = Depends(get_db),
):
    try:
        token_data   = await ig_fb_client.get_access_token(code)
        short_token  = token_data["access_token"]
        long_data    = await ig_fb_client.get_long_lived_token(short_token)
        access_token = long_data.get("access_token", short_token)
        expires_in   = long_data.get("expires_in", 5184000)  # 60 days default
        expires_at   = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Páginas
        pages = await ig_fb_client.get_pages(access_token)
        for page in pages:
            page_id    = page["id"]
            page_token = page.get("access_token", access_token)

            # Salvar/atualizar Facebook page
            existing_fb = (await db.execute(
                select(FacebookAccount).where(FacebookAccount.page_id == page_id)
            )).scalar()
            if existing_fb:
                existing_fb.access_token = page_token
                existing_fb.page_name    = page.get("name")
                existing_fb.avatar_url   = page.get("picture", {}).get("data", {}).get("url")
                existing_fb.token_expires_at = expires_at
                existing_fb.is_active    = True
            else:
                db.add(FacebookAccount(
                    page_id      = page_id,
                    page_name    = page.get("name"),
                    page_url     = f"https://facebook.com/{page_id}",
                    avatar_url   = page.get("picture", {}).get("data", {}).get("url"),
                    access_token = page_token,
                    token_expires_at = expires_at,
                ))

            # Instagram vinculado à página
            ig_info = await ig_fb_client.get_instagram_account(page_id, page_token)
            if ig_info:
                existing_ig = (await db.execute(
                    select(InstagramAccount).where(InstagramAccount.instagram_id == ig_info["id"])
                )).scalar()
                if existing_ig:
                    existing_ig.access_token     = page_token
                    existing_ig.username         = ig_info.get("username")
                    existing_ig.display_name     = ig_info.get("name")
                    existing_ig.avatar_url       = ig_info.get("profile_picture_url")
                    existing_ig.token_expires_at = expires_at
                    existing_ig.is_active        = True
                else:
                    db.add(InstagramAccount(
                        instagram_id  = ig_info["id"],
                        username      = ig_info.get("username"),
                        display_name  = ig_info.get("name"),
                        avatar_url    = ig_info.get("profile_picture_url"),
                        access_token  = page_token,
                        token_expires_at = expires_at,
                    ))

        await db.commit()
        return {"status": "success", "pages_connected": len(pages)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro OAuth Facebook: {str(e)}")


# ─── Disconnect ───────────────────────────────────────────────────────────────

@router.delete("/accounts/{platform}")
async def disconnect_account(
    platform: str,
    _:  str           = Depends(require_admin),
    db: AsyncSession  = Depends(get_db),
):
    if platform == "tiktok":
        acct = (await db.execute(select(TikTokAccount).where(TikTokAccount.account_type == "admin"))).scalar()
    elif platform == "youtube":
        acct = (await db.execute(select(YouTubeAccount).where(YouTubeAccount.is_active == True))).scalar()
    elif platform == "instagram":
        acct = (await db.execute(select(InstagramAccount).where(InstagramAccount.is_active == True))).scalar()
    elif platform == "facebook":
        acct = (await db.execute(select(FacebookAccount).where(FacebookAccount.is_active == True))).scalar()
    else:
        raise HTTPException(status_code=400, detail="Plataforma inválida")

    if not acct:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    acct.is_active = False
    await db.commit()
    return {"status": "disconnected", "platform": platform}


# ─── Upload ───────────────────────────────────────────────────────────────────

MAX_UPLOAD_BYTES = int(os.environ.get("ALETUBE_MAX_UPLOAD_MB", "500")) * 1024 * 1024


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    _:    str        = Depends(require_admin),
    db:   AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    file_ext = file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in ["mp4", "mov", "avi", "mkv"]:
        raise HTTPException(status_code=400, detail="Formato não suportado (mp4, mov, avi, mkv)")

    file_id   = uuid.uuid4().hex
    file_path = f"{VIDEOS_DIR}/{file_id}.{file_ext}"

    file_size = 0
    chunk_size = 1024 * 1024  # 1 MiB
    try:
        with open(file_path, "wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_BYTES:
                    out.close()
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"Ficheiro excede o limite de {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        try:
            os.remove(file_path)
        except OSError:
            pass
        # ENOSPC = 28 → disco cheio (filesystem efêmero do HF Space)
        if getattr(exc, "errno", None) == 28:
            raise HTTPException(status_code=507, detail="Sem espaço em disco no servidor.")
        raise HTTPException(status_code=500, detail=f"Erro de I/O: {exc}")
    except Exception as e:  # noqa: BLE001
        try:
            os.remove(file_path)
        except OSError:
            pass
        log.exception("aletube upload falhou (%s)", file.filename)
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {e}")

    video = AdminVideo(
        id        = uuid.uuid4(),
        filename  = file.filename,
        file_path = file_path,
        file_size_bytes = file_size,
        plataformas     = ["tiktok", "youtube"],
        publish_status  = "pending",
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "video_id":        str(video.id),
        "filename":        file.filename,
        "file_size_bytes": file_size,
        "status":          "ready_for_analysis",
    }


# ─── Analyze ─────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_video(
    video_id: str = Form(...),
    _:        str = Depends(require_admin),
    db:       AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video  = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    if not os.path.exists(video.file_path):
        raise HTTPException(status_code=400, detail="Arquivo não encontrado no servidor")

    # Extrai metadata real
    meta = await _extract_video_metadata(video.file_path)

    # Gera conteúdo por plataforma
    platform_content = await _generate_platform_content(
        video.filename,
        meta["duration_seconds"],
        meta["width"],
        meta["height"],
    )

    # Usa TikTok como "padrão" para campos legados
    tiktok_data = platform_content.get("tiktok", {})

    video.title             = tiktok_data.get("title", video.filename)
    video.description       = tiktok_data.get("description", "")
    video.hashtags          = tiktok_data.get("hashtags", [])
    video.duration_seconds  = meta["duration_seconds"]
    video.platform_metadata = platform_content

    await db.commit()
    await db.refresh(video)

    return {
        "video_id":         str(video.id),
        "duration_seconds": video.duration_seconds,
        "width":            meta["width"],
        "height":           meta["height"],
        "fps":              meta["fps"],
        "platform_metadata": platform_content,
    }


# ─── Publish ─────────────────────────────────────────────────────────────────

@router.post("/publish")
async def publish_video(
    video_id:      str           = Form(...),
    plataformas:   Optional[str] = Form(default="tiktok,youtube"),
    affiliate_url: Optional[str] = Form(default=None),
    # Metadados opcionais por plataforma (JSON string)
    tiktok_meta:   Optional[str] = Form(default=None),
    youtube_meta:  Optional[str] = Form(default=None),
    instagram_meta: Optional[str] = Form(default=None),
    facebook_meta: Optional[str] = Form(default=None),
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video  = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    if not video.platform_metadata:
        raise HTTPException(status_code=400, detail="Analise o vídeo primeiro (/analyze)")

    plats = [p.strip() for p in plataformas.split(",") if p.strip() in ["tiktok", "youtube", "instagram", "facebook"]]
    if not plats:
        raise HTTPException(status_code=400, detail="Nenhuma plataforma válida")

    # Parsear overrides de metadata por plataforma
    def _parse_meta(raw: Optional[str], fallback_key: str) -> dict:
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return (video.platform_metadata or {}).get(fallback_key, {})

    tt_meta = _parse_meta(tiktok_meta, "tiktok")
    yt_meta = _parse_meta(youtube_meta, "youtube")
    ig_meta = _parse_meta(instagram_meta, "instagram")
    fb_meta = _parse_meta(facebook_meta, "facebook")

    video.plataformas     = plats
    video.publish_status  = "publishing"
    results_by_platform   = {}

    async def _make_short_link(source: str, campaign: str) -> Optional[str]:
        if not affiliate_url:
            return None
        code = None
        for _ in range(10):
            candidate = _generate_code(8)
            existing  = await db.execute(select(ShortLink).where(ShortLink.code == candidate))
            if not existing.scalar():
                code = candidate
                break
        if not code:
            return None
        link = ShortLink(
            code          = code,
            affiliate_url = affiliate_url,
            provider      = "aletube",
            product_title = (video.title or "")[:200],
            source        = source,
            campaign      = campaign,
        )
        db.add(link)
        return f"https://bestpricetoday.vercel.app/r/{code}"

    # ── TikTok ──
    if "tiktok" in plats:
        try:
            tt_acct = (await db.execute(
                select(TikTokAccount).where(TikTokAccount.account_type == "admin", TikTokAccount.is_active == True)
            )).scalar()
            if not tt_acct:
                results_by_platform["tiktok"] = {"status": "error", "error": "Conta TikTok admin não conectada"}
            else:
                short_link = await _make_short_link("tiktok_admin", f"video_{video.id}")
                hashtags_str = " ".join(tt_meta.get("hashtags", []))
                description  = f"{tt_meta.get('description', '')}\n\n{hashtags_str}".strip()
                # Convert local path to public URL
                video_url = _get_public_video_url(str(video.id))
                tt_result = await tiktok_client.admin_publish_video(
                    access_token  = tt_acct.access_token,
                    video_url     = video_url,
                    title         = tt_meta.get("title", video.title or "")[:150],
                    description   = description[:2200],
                    tracked_link  = short_link,
                )
                video.tiktok_video_id  = tt_result.get("data", {}).get("publish_id") or tt_result.get("video_id")
                video.tiktok_short_link = short_link
                tt_acct.publishes_count += 1
                results_by_platform["tiktok"] = {"status": "ok", "short_link": short_link}
        except Exception as e:
            results_by_platform["tiktok"] = {"status": "error", "error": str(e)}

    # ── YouTube ──
    if "youtube" in plats:
        try:
            yt_acct = (await db.execute(
                select(YouTubeAccount).where(YouTubeAccount.is_active == True)
            )).scalar()
            if not yt_acct:
                results_by_platform["youtube"] = {"status": "error", "error": "Conta YouTube não conectada"}
            else:
                # Refresh token se necessário
                if yt_acct.token_expires_at and yt_acct.token_expires_at < datetime.now(timezone.utc):
                    refreshed = await youtube_client.refresh_token(yt_acct.refresh_token)
                    yt_acct.access_token     = refreshed["access_token"]
                    yt_acct.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=refreshed.get("expires_in", 3600))

                short_link  = await _make_short_link("youtube_admin", f"video_yt_{video.id}")
                description = yt_meta.get("description", "")
                if short_link:
                    description = f"{description}\n\n🛒 {short_link}"

                yt_result = await youtube_client.upload_video(
                    access_token = yt_acct.access_token,
                    file_path    = video.file_path,
                    title        = yt_meta.get("title", video.title or "")[:100],
                    description  = description[:5000],
                    tags         = yt_meta.get("hashtags", [])[:15],
                )
                video.youtube_video_id  = yt_result.get("video_id")
                video.youtube_short_link = short_link
                yt_acct.publishes_count += 1
                results_by_platform["youtube"] = {
                    "status": "ok",
                    "video_id": yt_result.get("video_id"),
                    "video_url": yt_result.get("video_url"),
                    "short_link": short_link,
                }
        except Exception as e:
            results_by_platform["youtube"] = {"status": "error", "error": str(e)}

    # ── Instagram ──
    if "instagram" in plats:
        try:
            ig_acct = (await db.execute(
                select(InstagramAccount).where(InstagramAccount.is_active == True)
            )).scalar()
            if not ig_acct:
                results_by_platform["instagram"] = {"status": "error", "error": "Conta Instagram não conectada"}
            else:
                short_link   = await _make_short_link("instagram_admin", f"video_ig_{video.id}")
                hashtags_str = " ".join(f"#{h.lstrip('#')}" for h in ig_meta.get("hashtags", []))
                caption      = f"{ig_meta.get('description', '')}\n\n{hashtags_str}".strip()
                if short_link:
                    caption = f"{caption}\n\n🛒 Link na bio"
                # Instagram requer URL pública do vídeo
                video_url = _get_public_video_url(str(video.id))
                ig_result = await ig_fb_client.publish_reel_instagram(
                    ig_account_id = ig_acct.instagram_id,
                    access_token  = ig_acct.access_token,
                    video_url     = video_url,
                    caption       = caption[:2200],
                )
                video.instagram_media_id   = ig_result.get("media_id")
                video.instagram_short_link = short_link
                ig_acct.publishes_count += 1
                results_by_platform["instagram"] = {"status": "ok", "media_id": ig_result.get("media_id"), "short_link": short_link}
        except Exception as e:
            results_by_platform["instagram"] = {"status": "error", "error": str(e)}

    # ── Facebook ──
    if "facebook" in plats:
        try:
            fb_acct = (await db.execute(
                select(FacebookAccount).where(FacebookAccount.is_active == True)
            )).scalar()
            if not fb_acct:
                results_by_platform["facebook"] = {"status": "error", "error": "Página Facebook não conectada"}
            else:
                short_link = await _make_short_link("facebook_admin", f"video_fb_{video.id}")
                description = fb_meta.get("description", "")
                if short_link:
                    description = f"{description}\n\n👉 {short_link}"
                fb_result = await ig_fb_client.publish_video_facebook(
                    page_id    = fb_acct.page_id,
                    page_token = fb_acct.access_token,
                    file_path  = video.file_path,
                    title      = fb_meta.get("title", video.title or "")[:255],
                    description = description,
                )
                video.facebook_post_id    = fb_result.get("id")
                video.facebook_short_link = short_link
                fb_acct.publishes_count += 1
                results_by_platform["facebook"] = {"status": "ok", "post_id": fb_result.get("id"), "short_link": short_link}
        except Exception as e:
            results_by_platform["facebook"] = {"status": "error", "error": str(e)}

    # Status geral
    any_ok    = any(v.get("status") == "ok" for v in results_by_platform.values())
    all_error = all(v.get("status") == "error" for v in results_by_platform.values())
    all_ok    = bool(results_by_platform) and all(v.get("status") == "ok" for v in results_by_platform.values())
    video.publish_status = "failed" if all_error else "published"
    video.published_at   = datetime.now(timezone.utc) if any_ok else None

    await db.commit()
    await db.refresh(video)

    # Cleanup: se TODAS as plataformas publicaram OK, apaga ficheiro local em background.
    # O delay dá tempo a TikTok/Instagram (que buscam por URL pública) descarregarem.
    if all_ok and video.file_path and not video.file_path.startswith("http"):
        asyncio.create_task(_cleanup_local_file(str(video.id), video.file_path))

    return {
        "video_id":  str(video.id),
        "status":    video.publish_status,
        "platforms": results_by_platform,
    }


async def _cleanup_local_file(video_id: str, file_path: str, delay_seconds: int = 180) -> None:
    """Apaga arquivo local após publish bem-sucedido em todas as plataformas."""
    try:
        await asyncio.sleep(delay_seconds)
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            log.info("aletube cleanup: removido %s (video %s)", file_path, video_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("aletube cleanup falhou para %s: %s", video_id, exc)


# ─── List Videos ─────────────────────────────────────────────────────────────

@router.get("/videos")
async def list_videos(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminVideo).order_by(AdminVideo.created_at.desc()))
    videos = result.scalars().all()
    return {
        "total": len(videos),
        "videos": [
            {
                "id":               str(v.id),
                "filename":         v.filename,
                "title":            v.title,
                "status":           v.publish_status,
                "plataformas":      v.plataformas,
                "tiktok_video_id":  v.tiktok_video_id,
                "youtube_video_id": v.youtube_video_id,
                "instagram_media_id": v.instagram_media_id if hasattr(v, 'instagram_media_id') else None,
                "facebook_post_id": v.facebook_post_id if hasattr(v, 'facebook_post_id') else None,
                "tiktok_views":     v.tiktok_views,
                "youtube_views":    v.youtube_views,
                "clicks_total":     v.clicks_total,
                "conversions":      v.conversions,
                "published_at":     v.published_at.isoformat() if v.published_at else None,
            }
            for v in videos
        ],
    }


@router.get("/serve/{video_id}")
async def serve_video(
    video_id: str,
    db:       AsyncSession = Depends(get_db),
):
    """Serve video file for public access (used for TikTok/Instagram/Facebook uploads)."""
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado no banco de dados")
    
    # Tentar locais possíveis de arquivo
    possible_paths = [
        video.file_path,  # Original
        f"/app/videos/{video_id}.mp4",  # HF Space persistente
        f"/tmp/aletube_videos/{video_id}.mp4",  # Fallback /tmp
    ]
    
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break
    
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo de vídeo não encontrado em nenhum local. Tente fazer re-upload do vídeo. (Video ID: {video_id})"
        )
    
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=video.filename,
    )
