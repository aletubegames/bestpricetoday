"""
TikTok endpoints — BestPriceToday
===================================

Fluxo USUÁRIO COMUM:
  GET  /tiktok/auth/user         → URL OAuth Login Kit (escopos básicos)
  GET  /tiktok/callback          → troca code → token, salva TikTokAccount
  POST /tiktok/share/link        → gera short link rastreado + Share Kit URL
  GET  /tiktok/account/me        → info da conta TikTok conectada do usuário

Fluxo ADMIN:
  GET  /tiktok/auth/admin        → URL OAuth (escopos admin + video.publish)
  POST /tiktok/admin/publish     → publica vídeo via Content Posting API (admin only)
  GET  /tiktok/admin/account     → info da conta admin conectada

Notas:
  - Content Posting API → SOMENTE admin (is_admin=True ou X-Admin-Key)
  - Share Kit → usuário comum, plataforma NÃO publica por ele
  - O link de afiliado rastreado SEMPRE aponta para BestPriceToday, comissão nossa
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.integrations.tiktok import tiktok_client
from app.models.models import TikTokAccount, ShortLink, ClickEvent, User
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
import secrets
import string
import uuid as _uuid

router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _generate_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> bool:
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Acesso admin necessário")
    return True


# ─── USUÁRIO COMUM ────────────────────────────────────────────────────────────

@router.get("/auth/user")
async def tiktok_user_auth():
    """
    Inicia o fluxo OAuth para usuário comum.
    Escopos: user.info.basic, user.info.profile (sem video.publish)
    """
    state = str(_uuid.uuid4())
    auth_url = tiktok_client.get_user_auth_url(state)
    return {
        "auth_url": auth_url,
        "state": state,
        "flow": "user",
        "scopes": "user.info.basic,user.info.profile",
        "note": "Login Kit apenas. Publicação feita pelo próprio usuário via Share Kit.",
    }


@router.get("/callback")
async def tiktok_callback(
    code: str,
    state: str,
    mode: Optional[str] = Query(default="user"),  # "user" | "admin"
    db: AsyncSession = Depends(get_db),
):
    """
    Callback OAuth TikTok.
    Troca o code pelo access_token e salva/atualiza TikTokAccount.
    """
    try:
        token_data = await tiktok_client.get_access_token(code)
        data       = token_data.get("data", token_data)

        access_token  = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in    = data.get("expires_in", 86400)
        open_id       = data.get("open_id")
        scopes        = data.get("scope", "")

        if not access_token or not open_id:
            raise HTTPException(status_code=400, detail="Token inválido recebido do TikTok")

        # Buscar perfil do usuário
        user_info = await tiktok_client.get_user_info(access_token)
        profile   = user_info.get("data", {}).get("user", {})

        # Upsert TikTokAccount
        result  = await db.execute(select(TikTokAccount).where(TikTokAccount.tiktok_open_id == open_id))
        account = result.scalar()

        if account:
            account.access_token     = access_token
            account.refresh_token    = refresh_token
            account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            account.scopes           = scopes
            account.display_name     = profile.get("display_name") or account.display_name
            account.avatar_url       = profile.get("avatar_url") or account.avatar_url
            account.is_verified      = profile.get("is_verified", False)
            account.profile_link     = profile.get("profile_deep_link") or account.profile_link
            account.updated_at       = datetime.now(timezone.utc)
            account.account_type     = mode
            account.is_active        = True
        else:
            account = TikTokAccount(
                tiktok_open_id   = open_id,
                tiktok_union_id  = data.get("union_id"),
                account_type     = mode,
                display_name     = profile.get("display_name"),
                avatar_url       = profile.get("avatar_url"),
                is_verified      = profile.get("is_verified", False),
                profile_link     = profile.get("profile_deep_link"),
                access_token     = access_token,
                refresh_token    = refresh_token,
                token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in),
                scopes           = scopes,
            )
            db.add(account)

        await db.commit()
        await db.refresh(account)

        return {
            "status":       "success",
            "message":      "Conta TikTok conectada com sucesso!",
            "account_type": account.account_type,
            "display_name": account.display_name,
            "avatar_url":   account.avatar_url,
            "is_verified":  account.is_verified,
            "scopes":       scopes,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro na autorização TikTok: {str(e)}")


@router.get("/account/me")
async def tiktok_my_account(
    open_id: str = Query(..., description="TikTok open_id do usuário"),
    db: AsyncSession = Depends(get_db),
):
    """Retorna informações da conta TikTok conectada."""
    result  = await db.execute(select(TikTokAccount).where(TikTokAccount.tiktok_open_id == open_id))
    account = result.scalar()
    if not account:
        raise HTTPException(status_code=404, detail="Conta TikTok não encontrada")
    return {
        "display_name":  account.display_name,
        "avatar_url":    account.avatar_url,
        "is_verified":   account.is_verified,
        "profile_link":  account.profile_link,
        "account_type":  account.account_type,
        "scopes":        account.scopes,
        "shares_count":  account.shares_count,
        "connected_at":  account.created_at.isoformat() if account.created_at else None,
    }


# ─── SHARE KIT (usuário comum) ────────────────────────────────────────────────

class ShareLinkRequest(BaseModel):
    affiliate_url:  str
    provider:       Optional[str]  = None
    product_title:  Optional[str]  = None
    price:          Optional[float] = None
    tiktok_open_id: Optional[str]  = None  # para vincular ao usuário
    video_url:      Optional[str]  = None  # opcional: vídeo para download


@router.post("/share/link")
async def create_share_link(
    data: ShareLinkRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Cria um short link rastreado e gera a URL do Share Kit.

    Fluxo:
    1. Cria ShortLink com source="tiktok_user"
    2. Monta legenda + hashtags
    3. Gera Share Kit URL (usuário abre o TikTok e compartilha por conta própria)
    4. Comissão sempre vinculada ao link BestPriceToday

    A plataforma NÃO publica automaticamente — é o usuário que decide.
    """
    try:
        # 1. Gerar short link rastreado
        code = None
        for _ in range(10):
            candidate = _generate_code(8)
            existing  = await db.execute(select(ShortLink).where(ShortLink.code == candidate))
            if not existing.scalar():
                code = candidate
                break

        if not code:
            raise HTTPException(status_code=500, detail="Falha ao gerar código único")

        short_link_url = f"https://bestpricetoday.vercel.app/r/{code}"

        link = ShortLink(
            code          = code,
            affiliate_url = data.affiliate_url,
            provider      = data.provider,
            product_title = data.product_title[:200] if data.product_title else None,
            price         = data.price,
            source        = "tiktok_user",
            campaign      = "tiktok_share",
        )
        db.add(link)

        # 2. Montar legenda
        name     = (data.product_title or "produto")[:60]
        price    = f"R$ {data.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if data.price else ""
        provider = (data.provider or "loja").capitalize()

        caption = (
            f"🔥 Oferta imperdível: {name}\n"
            f"{'💰 ' + price + ' ' if price else ''}"
            f"no {provider}!\n\n"
            f"🛒 Link na bio ⬆️\n"
            f"{short_link_url}\n\n"
            f"Encontrei no BestPriceToday — compara preços em {provider}, Amazon, Shopee e mais!"
        )

        hashtags = "#oferta #desconto #promoção #bestpricetoday #economize #dica #tiktokbrasil"
        if data.provider:
            hashtags += f" #{data.provider.lower()}"

        # 3. Gerar Share Kit URL
        share_kit_url = tiktok_client.build_share_url(
            short_link = short_link_url,
            caption    = caption,
            hashtags   = hashtags,
            video_url  = data.video_url,
        )

        # 4. Atualizar contador da conta TikTok se open_id fornecido
        if data.tiktok_open_id:
            result  = await db.execute(
                select(TikTokAccount).where(TikTokAccount.tiktok_open_id == data.tiktok_open_id)
            )
            account = result.scalar()
            if account:
                account.shares_count += 1

        await db.commit()

        return {
            "code":           code,
            "short_link":     short_link_url,
            "share_kit_url":  share_kit_url,
            "caption":        caption,
            "hashtags":       hashtags,
            "note": (
                "Abra o share_kit_url para compartilhar no TikTok. "
                "A comissão é rastreada pelo short_link independente de quem postou."
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar link: {str(e)}")


# ─── ADMIN ────────────────────────────────────────────────────────────────────

@router.get("/auth/admin")
async def tiktok_admin_auth(
    _: bool = Depends(_verify_admin_key),
):
    """
    Inicia OAuth para conta admin da plataforma.
    Escopos: user.info.basic + video.publish + video.upload (Content Posting API)
    USO EXCLUSIVO ADMIN.
    """
    state    = str(_uuid.uuid4())
    auth_url = tiktok_client.get_admin_auth_url(state)
    return {
        "auth_url": auth_url,
        "state":    state,
        "flow":     "admin",
        "scopes":   "user.info.basic,user.info.profile,video.publish,video.upload",
        "warning":  "Content Posting API — uso exclusivo conta admin BestPriceToday",
    }


@router.get("/admin/account")
async def tiktok_admin_account(
    _:  bool               = Depends(_verify_admin_key),
    db: AsyncSession       = Depends(get_db),
):
    """Retorna a conta admin TikTok conectada."""
    result  = await db.execute(
        select(TikTokAccount).where(TikTokAccount.account_type == "admin", TikTokAccount.is_active == True)
    )
    account = result.scalar()
    if not account:
        return {"connected": False, "message": "Nenhuma conta admin TikTok conectada"}
    return {
        "connected":       True,
        "display_name":    account.display_name,
        "avatar_url":      account.avatar_url,
        "is_verified":     account.is_verified,
        "profile_link":    account.profile_link,
        "scopes":          account.scopes,
        "publishes_count": account.publishes_count,
        "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
    }


class AdminPublishRequest(BaseModel):
    video_url:      str
    title:          str
    description:    str
    affiliate_url:  Optional[str]  = None  # para gerar tracked link e incluir na description
    provider:       Optional[str]  = None
    product_title:  Optional[str]  = None
    price:          Optional[float] = None


@router.post("/admin/publish")
async def admin_publish_video(
    data: AdminPublishRequest,
    _:    bool         = Depends(_verify_admin_key),
    db:   AsyncSession = Depends(get_db),
):
    """
    Publica vídeo na conta admin do TikTok via Content Posting API.
    USO EXCLUSIVO ADMIN.

    Se affiliate_url for fornecido, cria um short link rastreado
    e o inclui na description antes de publicar.
    """
    # Buscar conta admin ativa
    result  = await db.execute(
        select(TikTokAccount).where(TikTokAccount.account_type == "admin", TikTokAccount.is_active == True)
    )
    account = result.scalar()
    if not account:
        raise HTTPException(status_code=400, detail="Conta admin TikTok não conectada. Use /tiktok/auth/admin primeiro.")

    # Verificar token expirado
    if account.token_expires_at and datetime.now(timezone.utc) > account.token_expires_at:
        if account.refresh_token:
            try:
                refreshed    = await tiktok_client.refresh_access_token(account.refresh_token)
                rd           = refreshed.get("data", refreshed)
                account.access_token     = rd["access_token"]
                account.refresh_token    = rd.get("refresh_token", account.refresh_token)
                account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=rd.get("expires_in", 86400))
                await db.commit()
            except Exception:
                raise HTTPException(status_code=401, detail="Token TikTok expirado. Reconecte a conta admin.")
        else:
            raise HTTPException(status_code=401, detail="Token TikTok expirado. Reconecte a conta admin.")

    # Gerar short link rastreado se houver URL de afiliado
    tracked_link = None
    if data.affiliate_url:
        code = None
        for _ in range(10):
            candidate = _generate_code(8)
            existing  = await db.execute(select(ShortLink).where(ShortLink.code == candidate))
            if not existing.scalar():
                code = candidate
                break

        if code:
            tracked_link = f"https://bestpricetoday.vercel.app/r/{code}"
            link = ShortLink(
                code          = code,
                affiliate_url = data.affiliate_url,
                provider      = data.provider,
                product_title = data.product_title[:200] if data.product_title else None,
                price         = data.price,
                source        = "tiktok_admin",
                campaign      = "admin_publish",
            )
            db.add(link)

    # Publicar via Content Posting API
    try:
        result_pub = await tiktok_client.admin_publish_video(
            access_token  = account.access_token,
            video_url     = data.video_url,
            title         = data.title,
            description   = data.description,
            tracked_link  = tracked_link,
        )

        # Atualizar contador
        account.publishes_count += 1
        await db.commit()

        return {
            "status":       "success",
            "publish_data": result_pub,
            "tracked_link": tracked_link,
            "message":      "Vídeo publicado na conta TikTok admin.",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao publicar no TikTok: {str(e)}")
