"""
Redirect endpoint — tracked affiliate links.
GET /r/{code} → register click + 302 redirect to affiliate URL
POST /links/create → create a new short link, returns the code
GET /img/proxy/{encoded} → proxy de imagem (para Instagram Graph API)
"""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.core.config import settings
from app.models.models import ShortLink, ClickEvent
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import secrets
import string
import base64
import httpx

router = APIRouter()


def generate_code(length: int = 8) -> str:
    """Generate a random short code."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class CreateLinkRequest(BaseModel):
    affiliate_url: str
    provider: Optional[str] = None
    product_title: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    original_price: Optional[float] = None
    source: str = "video"
    campaign: Optional[str] = None


@router.post("/links/create")
async def create_short_link(
    data: CreateLinkRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a tracked short link. Rate limited per IP.
    """
    from app.core.rate_limit import check_rate_limit, get_client_ip
    ip = get_client_ip(request)
    max_calls = settings.RATE_LIMIT_PER_MINUTE
    if not await check_rate_limit(ip, key="links_create", max_calls=max_calls, window_seconds=60):
        return JSONResponse(status_code=429, content={"error": f"Rate limit exceeded. Max {max_calls} links/min per IP."})
    try:
        # Generate unique code
        for _ in range(10):
            code = generate_code(8)
            existing = await db.execute(select(ShortLink).where(ShortLink.code == code))
            if not existing.scalar():
                break

        link = ShortLink(
            code=code,
            affiliate_url=data.affiliate_url,
            provider=data.provider,
            product_title=data.product_title[:200] if data.product_title else None,
            price=data.price,
            image_url=data.image_url,
            original_price=data.original_price,
            source=data.source,
            campaign=data.campaign,
        )
        db.add(link)
        await db.commit()

        return {
            "code": code,
            "url": f"{settings.PUBLIC_SITE_URL}/r/{code}",
            "short_url": f"{settings.PUBLIC_SITE_URL}/r/{code}",
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/r/{code}")
async def redirect_link(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Tracked redirect — agora vai para a página de oferta no frontend.
    1. Find link by code
    2. 302 redirect para /oferta/{code} (página com botão VER OFERTA)
    O clique real é registrado em /r/{code}/go quando o usuário clica no botão.
    """
    try:
        result = await db.execute(select(ShortLink).where(ShortLink.code == code))
        link = result.scalar()

        if not link:
            return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)

        # Redirect para a página de oferta no frontend
        return RedirectResponse(
            url=f"{settings.PUBLIC_SITE_URL}/oferta/{code}",
            status_code=302,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
            }
        )

    except Exception:
        return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)


@router.get("/r/{code}/info")
async def get_link_info(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna informações da oferta associada ao short link (sem redirecionar).
    Usado pela página /oferta/{code} no frontend para mostrar o produto
    com botão "VER OFERTA" antes de redirecionar para a loja.
    """
    result = await db.execute(select(ShortLink).where(ShortLink.code == code))
    link = result.scalar()

    if not link:
        return JSONResponse(status_code=404, content={"error": "Link not found"})

    return {
        "code": link.code,
        "product_title": link.product_title,
        "price": link.price,
        "original_price": link.original_price,
        "image_url": link.image_url,
        "provider": link.provider,
        "affiliate_url": link.affiliate_url,
        "source": link.source,
        "clicks": link.clicks,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


@router.get("/r/{code}/go")
async def redirect_to_store(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Redireciona para a loja (afiliado).
    Usado quando o usuário clica em "VER OFERTA" na página /oferta/{code}.
    Registra o clique e faz 302 redirect para o affiliate_url.
    """
    try:
        result = await db.execute(select(ShortLink).where(ShortLink.code == code))
        link = result.scalar()

        if not link:
            return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)

        # Register click
        click = ClickEvent(
            offer_id=str(link.id),
            provider=link.provider,
            product_title=link.product_title,
            price=link.price,
            affiliate_url=link.affiliate_url,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            source=link.source or "video",
        )
        db.add(click)
        link.clicks += 1
        link.last_clicked_at = datetime.now(timezone.utc)
        await db.commit()

        return RedirectResponse(
            url=link.affiliate_url,
            status_code=302,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Redirect-To": link.provider or "affiliate",
            }
        )
    except Exception:
        return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)


@router.get("/img/proxy/{encoded}")
async def proxy_image(encoded: str):
    """Proxy de imagem para Instagram Graph API.
    Baixa a imagem da URL original (codificada em base64) e serve
    como JPEG (Instagram exige JPEG/PNG). Necessário porque o Instagram
    rejeita URLs de alguns CDNs (AliExpress, vteximg, etc) e formatos webp.
    """
    try:
        # Decodifica base64
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        original_url = base64.urlsafe_b64decode(encoded).decode()

        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(original_url, follow_redirects=True)
            if r.status_code != 200:
                return Response(status_code=404)

        # Converte para JPEG usando PIL (Instagram não aceita webp)
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            content = buf.getvalue()
        except Exception:
            # Se PIL falhar, serve o conteúdo original
            content = r.content

        return Response(
            content=content,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except Exception:
        return Response(status_code=404)
