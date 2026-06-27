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
import re
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

VIDEOS_DIR = os.environ.get("ALETUBE_VIDEOS_DIR", "./videos")  # ✅ Usar ./videos local
os.makedirs(VIDEOS_DIR, exist_ok=True)

# Get INTERNAL_API_URL for serving videos publicly
INTERNAL_API_URL = os.environ.get("INTERNAL_API_URL", "https://sacrament-subduing-confined.ngrok-free.dev")


def _generate_code(length: int = 8) -> str:
    return uuid.uuid4().hex[:length].upper()


def _get_public_video_url(video_id: str) -> str:
    """Convert local video path to public URL."""
    return f"{INTERNAL_API_URL}/aletube/serve/{video_id}"


# ─── Análise IA com vision ───────────────────────────────────────────────────

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


def _extract_keyframes(file_path: str, duration_seconds: int, count: int = 4, max_dim: int = 768) -> list[bytes]:
    """Extrai N frames JPEG espaçados ao longo do vídeo (para análise visual da IA).

    Reduz dimensão máxima para max_dim para reduzir tokens de imagem.
    Retorna lista de bytes JPEG (ou lista vazia se falhar).
    """
    if duration_seconds <= 0 or count <= 0:
        return []
    # Timestamps espaçados — evita início e fim absolutos.
    step = duration_seconds / (count + 1)
    timestamps = [round(step * (i + 1), 2) for i in range(count)]
    frames: list[bytes] = []
    for ts in timestamps:
        try:
            proc = subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(ts), "-i", file_path,
                    "-frames:v", "1",
                    "-vf", f"scale='min({max_dim},iw)':'-2'",
                    "-q:v", "5",
                    "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
                ],
                capture_output=True, timeout=20,
            )
            if proc.returncode == 0 and proc.stdout:
                frames.append(proc.stdout)
        except Exception:
            continue
    return frames


def _ai_prompt(filename: str, duration_seconds: int, width: int, height: int, has_frames: bool) -> str:
    visual_hint = (
        "Analisa as imagens (frames extraídos do vídeo) para identificar o conteúdo real "
        "(jogo, personagens, género, ação, contexto). Sê específico — evita termos genéricos."
        if has_frames else
        "Sem frames visuais disponíveis — usa apenas o nome do ficheiro como pista. "
        "Mesmo assim, evita hashtags genéricas como #fyp #viral #tech se não houver razão concreta."
    )
    return f"""És um especialista em marketing de conteúdo para redes sociais (PT-BR e EN).

Vídeo: "{filename}"
Duração: {duration_seconds}s
Resolução: {width}x{height}px

{visual_hint}

Gera conteúdo otimizado por plataforma. Regras DURAS:
- Título e descrição ESPECÍFICOS ao que vês (ex: "Trickson Me parry-perfeito vence New Hex em SF3 3rd Strike"), não vagos.
- Hashtags relevantes ao conteúdo (jogo, personagem, género, comunidade) — não enche-chouriços.
- TikTok caption < 200 chars + CTA.
- YouTube description com 2-3 parágrafos, inclui keywords SEO + link https://bestpricetoday.vercel.app no final.
- Instagram caption emocional + emojis + 20-30 hashtags.
- Facebook texto mais conversacional, 3-5 hashtags.
- NÃO incluas markdown nem comentários. Resposta = JSON válido apenas.

Formato exacto:
{{
  "tiktok":    {{"title": "...", "description": "...", "hashtags": ["#tag1","#tag2"], "bio_note": "..."}},
  "youtube":   {{"title": "...", "description": "...", "hashtags": ["tag1","tag2"], "end_screen_note": "..."}},
  "instagram": {{"title": "...", "description": "...", "hashtags": ["tag1","tag2"], "bio_note": "..."}},
  "facebook":  {{"title": "...", "description": "...", "hashtags": ["tag1","tag2"], "bio_note": "..."}}
}}"""


def _smart_fallback(filename: str) -> dict:
    """Fallback offline: extrai tokens do filename para gerar conteúdo menos genérico."""
    raw = filename.rsplit(".", 1)[0]
    tokens = [t for t in re.split(r"[\s_\-\.]+", raw) if t]
    title = " ".join(t.capitalize() for t in tokens) or raw
    base_hash = [f"#{t.lower()}" for t in tokens if len(t) > 2 and t.isalnum()][:5]
    return {
        "tiktok":    {"title": title[:150], "description": f"🎮 {title}\n\n📲 Segue para mais!", "hashtags": base_hash or ["#aletubegames"], "bio_note": "Link na bio 🛒"},
        "youtube":   {"title": f"{title} | AleTubeGames"[:100], "description": f"{title}\n\n🛒 https://bestpricetoday.vercel.app", "hashtags": [t.lower() for t in tokens][:12] or ["aletubegames"], "end_screen_note": "Inscrição + vídeos relacionados"},
        "instagram": {"title": title[:100], "description": f"🎮 {title}\nLink na bio ⬆️", "hashtags": [t.lower() for t in tokens][:25] or ["aletubegames"], "bio_note": "Atualiza link na bio"},
        "facebook":  {"title": title[:255], "description": f"{title}\n\n👉 bestpricetoday.vercel.app", "hashtags": [t for t in tokens][:5] or ["AleTubeGames"], "bio_note": "Fixa link nos comentários"},
    }


def _parse_ai_json(text: str) -> Optional[dict]:
    text = text.strip()
    if text.startswith("```"):
        # remove fences
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
    try:
        return json.loads(text)
    except Exception:
        # tenta extrair primeiro objecto JSON
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None


async def _call_openrouter_vision(prompt: str, frames: list[bytes]) -> Optional[dict]:
    """Chama OpenRouter (OpenAI-compatible) com vision. Retorna JSON parseado ou None."""
    if not settings.OPENROUTER_API_KEY:
        return None
    import base64
    content: list[dict] = [{"type": "text", "text": prompt}]
    for f in frames:
        b64 = base64.b64encode(f).decode("ascii")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    payload = {
        "model": settings.OPENROUTER_MODEL or "anthropic/claude-3.5-sonnet",
        "max_tokens": 1500,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": content}],
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "https://bestpricetoday.vercel.app",
                    "X-Title":       "AleTubeGames",
                },
                json=payload,
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            return _parse_ai_json(text)
    except Exception as exc:  # noqa: BLE001
        log.warning("openrouter falhou: %s", exc)
        return None


async def _call_anthropic_text(prompt: str) -> Optional[dict]:
    """Fallback para Anthropic direto (sem vision, modelo barato)."""
    if not settings.ANTHROPIC_API_KEY:
        return None
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
                    "model":      "claude-3-5-haiku-20241022",
                    "max_tokens": 1500,
                    "messages":   [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return _parse_ai_json(r.json()["content"][0]["text"])
    except Exception as exc:  # noqa: BLE001
        log.warning("anthropic direct falhou: %s", exc)
        return None


async def _generate_platform_content(
    filename: str,
    duration_seconds: int,
    width: int,
    height: int,
    file_path: Optional[str] = None,
) -> dict:
    """Gera conteúdo por plataforma. Cascata: OpenRouter (vision) → Anthropic → fallback."""
    frames: list[bytes] = []
    if file_path and settings.OPENROUTER_API_KEY:
        try:
            frames = _extract_keyframes(file_path, duration_seconds, count=4)
            log.info("aletube analyze: extraídos %d frames de %s", len(frames), filename)
        except Exception as exc:  # noqa: BLE001
            log.warning("aletube extract frames falhou: %s", exc)

    prompt = _ai_prompt(filename, duration_seconds, width, height, has_frames=bool(frames))

    if settings.OPENROUTER_API_KEY:
        result = await _call_openrouter_vision(prompt, frames)
        if result:
            return result

    if settings.ANTHROPIC_API_KEY:
        result = await _call_anthropic_text(prompt)
        if result:
            return result

    return _smart_fallback(filename)


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
        # Banco pode guardar datetime offset-naive; converte para UTC-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
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
    if not (settings.ID_APLICATIVO_FACEBOOK or settings.ID_APLICATIVO_INSTAGRAM or settings.INSTAGRAM_APP_ID):
        raise HTTPException(status_code=400, detail="ID_APLICATIVO_FACEBOOK ou ID_APLICATIVO_INSTAGRAM não configurado")
    return {"auth_url": auth_url, "state": state}


@router.get("/test/facebook-credentials")
async def test_facebook_credentials():
    """Testa se as credenciais Facebook estão corretas"""
    try:
        import httpx
        from app.core.config import settings
        
        log.info("Testando credenciais Facebook...")
        log.info(f"App ID: {settings.ID_APLICATIVO_FACEBOOK}")
        log.info(f"App Secret: {settings.FACEBOOK_APP_SECRET[:10]}..." if settings.FACEBOOK_APP_SECRET else "Secret não configurado")
        
        # Teste simples: tentar chamar a API com as credenciais
        params = {
            "client_id": settings.ID_APLICATIVO_FACEBOOK,
            "client_secret": settings.FACEBOOK_APP_SECRET,
            "grant_type": "client_credentials"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get("https://graph.facebook.com/v19.0/oauth/access_token", params=params)
            log.info(f"Credentials test status: {r.status_code}")
            log.info(f"Response: {r.text[:200]}")
            
            if r.status_code == 200:
                return {"status": "success", "credentials_valid": True, "response": r.json()}
            else:
                return {"status": "error", "credentials_valid": False, "error": r.text[:200]}
                
    except Exception as e:
        log.error(f"Erro ao testar credenciais: {str(e)}")
        return {"status": "error", "credentials_valid": False, "error": str(e)}


@router.get("/test/facebook-connectivity")
async def test_facebook_connectivity():
    """Testa conectividade com a API do Facebook"""
    try:
        import httpx
        log.info("Testando conectividade com Facebook API...")
        
        # Teste simples: fazer uma requisição para a API do Facebook
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Testar se consegue conectar com graph.facebook.com
            r = await client.get("https://graph.facebook.com/v19.0", timeout=10.0)
            log.info(f"Facebook connectivity test status: {r.status_code}")
            return {"status": "success", "facebook_api_reachable": True, "status_code": r.status_code}
    except httpx.TimeoutException:
        log.error("Timeout ao tentar conectar com Facebook API")
        return {"status": "error", "facebook_api_reachable": False, "error": "Timeout"}
    except httpx.NetworkError as e:
        log.error(f"Erro de rede ao conectar com Facebook API: {str(e)}")
        return {"status": "error", "facebook_api_reachable": False, "error": f"Network error: {str(e)}"}
    except Exception as e:
        log.error(f"Erro ao testar conectividade: {str(e)}")
        return {"status": "error", "facebook_api_reachable": False, "error": str(e)}


@router.get("/callback/facebook")
async def callback_facebook(
    code:  str,
    state: str,
    db:    AsyncSession  = Depends(get_db),
):
    try:
        log.info(f"Facebook callback recebido: code={code[:20] if code else 'None'}..., state={state}")

        if not code:
            log.error("Código OAuth não recebido")
            raise HTTPException(status_code=400, detail="Código OAuth não recebido")

        # Obter token do Facebook
        token_data = await ig_fb_client.get_access_token(code)
        log.info(f"Token obtido com sucesso: {list(token_data.keys())}")
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="access_token não retornado pelo Facebook")

        # Trocar por long-lived token (60 dias)
        try:
            ll = await ig_fb_client.get_long_lived_token(access_token)
            access_token = ll.get("access_token", access_token)
            expires_in = ll.get("expires_in", 5184000)  # 60 dias default
        except Exception as ll_err:
            log.warning(f"Não foi possível trocar por long-lived token: {ll_err}")
            expires_in = token_data.get("expires_in", 3600)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Páginas - com tratamento de erro para escopos limitados
        try:
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
                try:
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
                except Exception as ig_error:
                    log.warning(f"Não foi possível buscar conta Instagram: {ig_error}")

            await db.commit()
            return {"status": "success", "pages_connected": len(pages)}
        except Exception as pages_error:
            log.warning(f"Não foi possível buscar páginas Facebook (escopos limitados): {pages_error}")
            # Salvar pelo menos o token básico para mostrar como conectado
            existing_fb = (await db.execute(
                select(FacebookAccount).where(FacebookAccount.page_id == "user_token")
            )).scalar()
            if existing_fb:
                existing_fb.access_token = access_token
                existing_fb.token_expires_at = expires_at
                existing_fb.is_active = True
            else:
                db.add(FacebookAccount(
                    page_id      = "user_token",
                    page_name    = "Facebook User",
                    page_url     = "https://facebook.com",
                    access_token = access_token,
                    token_expires_at = expires_at,
                ))
            await db.commit()
            return {"status": "success", "pages_connected": 0, "note": "Conexão básica estabelecida (escopos limitados)"}
    except Exception as e:
        log.error(f"Erro OAuth Facebook: {str(e)}", exc_info=True)
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
        file_path=video.file_path,
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
                "created_at":       v.created_at.isoformat() if v.created_at else None,
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


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Apaga um vídeo (DB + ficheiro local se existir)."""
    result = await db.execute(select(AdminVideo).where(AdminVideo.id == video_id))
    video  = result.scalar()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    fp = video.file_path
    await db.delete(video)
    await db.commit()
    if fp and os.path.exists(fp):
        try:
            os.remove(fp)
        except Exception as exc:  # noqa: BLE001
            log.warning("delete file falhou: %s", exc)
    return {"ok": True, "id": video_id}


@router.post("/videos/cleanup-orphans")
async def cleanup_orphan_videos(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Remove da DB todos os vídeos cujo ficheiro local já não existe."""
    result = await db.execute(select(AdminVideo))
    videos = result.scalars().all()
    removed: list[str] = []
    for v in videos:
        if not v.file_path or not os.path.exists(v.file_path):
            removed.append(str(v.id))
            await db.delete(v)
    await db.commit()
    return {"ok": True, "removed_count": len(removed), "removed_ids": removed}


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


# ─── Local Publish (CLI) ─────────────────────────────────────────────────────
# Endpoints usados pelo CLI tools/aletube_youtube_upload.py para publicar
# vídeos grandes (>100MB) directamente da máquina do admin, sem passar
# pelo HF Space.

@router.get("/local/youtube-credentials")
async def local_youtube_credentials(
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retorna credenciais OAuth da conta YouTube ativa para uso pelo CLI local.

    ⚠ Endpoint sensível. Protegido por X-Admin-Key. Usado apenas por
    tools/aletube_youtube_upload.py em máquina do admin.
    """
    yt_acct = (await db.execute(
        select(YouTubeAccount).where(YouTubeAccount.is_active == True)
    )).scalar()
    if not yt_acct:
        raise HTTPException(status_code=404, detail="Nenhuma conta YouTube ativa")
    if not yt_acct.refresh_token:
        raise HTTPException(status_code=400, detail="Conta YouTube sem refresh_token. Reconectar.")
    if not (settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET):
        raise HTTPException(status_code=500, detail="YOUTUBE_CLIENT_ID/SECRET não configurados")
    return {
        "client_id":     settings.YOUTUBE_CLIENT_ID,
        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
        "refresh_token": yt_acct.refresh_token,
        "channel_id":    yt_acct.channel_id,
        "channel_title": yt_acct.channel_title,
    }


@router.post("/local/register-youtube-result")
async def local_register_youtube_result(
    youtube_video_id: str           = Form(...),
    title:            Optional[str] = Form(default=None),
    filename:         Optional[str] = Form(default=None),
    file_size_bytes:  Optional[int] = Form(default=None),
    duration_seconds: Optional[int] = Form(default=None),
    video_id:         Optional[str] = Form(default=None),  # se já existir AdminVideo
    _:  str          = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Regista resultado de upload local no DB (cria ou atualiza AdminVideo)."""
    video: Optional[AdminVideo] = None
    if video_id:
        video = (await db.execute(
            select(AdminVideo).where(AdminVideo.id == video_id)
        )).scalar()

    if video is None:
        video = AdminVideo(
            id              = uuid.uuid4(),
            filename        = filename or f"local_{youtube_video_id}.mp4",
            file_path       = "",  # sem ficheiro no servidor (upload foi local)
            file_size_bytes = file_size_bytes,
            duration_seconds = duration_seconds,
            title           = title,
            plataformas     = ["youtube"],
            publish_status  = "pending",
        )
        db.add(video)

    video.youtube_video_id = youtube_video_id
    video.publish_status   = "published"
    video.published_at     = datetime.now(timezone.utc)
    if title and not video.title:
        video.title = title

    yt_acct = (await db.execute(
        select(YouTubeAccount).where(YouTubeAccount.is_active == True)
    )).scalar()
    if yt_acct:
        yt_acct.publishes_count = (yt_acct.publishes_count or 0) + 1

    await db.commit()
    await db.refresh(video)

    return {
        "video_id":         str(video.id),
        "youtube_video_id": youtube_video_id,
        "youtube_url":      f"https://youtube.com/watch?v={youtube_video_id}",
        "status":           video.publish_status,
    }
