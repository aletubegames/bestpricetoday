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
from app.services.affiliate_tracking import add_ml_affiliate_tracking
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import secrets
import string
import base64
import httpx
import logging
from urllib.parse import urljoin, urlparse

router = APIRouter()
links_logger = logging.getLogger("links_create")

_IMAGE_ALLOWED_HOSTS = (
    "mlstatic.com",
    "alicdn.com",
    "aliexpress-media.com",
    "vteximg.com.br",
    "vtex.com.br",
    "shopee.com.br",
    "amazon.com",
    "kabum.com.br",
)


def _is_allowed_image_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and bool(host)
        and any(host == allowed or host.endswith(f".{allowed}") for allowed in _IMAGE_ALLOWED_HOSTS)
        and not parsed.username
        and not parsed.password
    )


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
    ua = request.headers.get("user-agent", "unknown")
    ref = request.headers.get("referer", "unknown")
    links_logger.info(
        "CREATE_SHORT_LINK source=%s campaign=%s ip=%s ua=%s ref=%s provider=%s title=%s price=%s",
        data.source, data.campaign, ip, ua, ref, data.provider,
        (data.product_title or "")[:50], data.price,
    )
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
    Tracked redirect — vai direto para a loja (afiliado).
    Registra o clique e faz 302 redirect para o affiliate_url.
    Se o link estiver marcado como morto (is_dead), mostra página de expirado.
    """
    try:
        result = await db.execute(select(ShortLink).where(ShortLink.code == code))
        link = result.scalar()

        if not link:
            return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)

        # Link quebrado — mostra página de oferta expirada
        if link.is_dead:
            return RedirectResponse(
                url=f"{settings.PUBLIC_SITE_URL}/oferta/{code}?expired=1",
                status_code=302,
            )

        # Register click
        click = ClickEvent(
            offer_id=str(link.id),
            provider=link.provider,
            product_title=link.product_title,
            price=link.price,
            affiliate_url=link.affiliate_url,
            ip_address=(
                request.headers.get("cf-connecting-ip")
                or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                or (request.client.host if request.client else None)
            ),
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            source=link.source or "video",
        )
        db.add(click)
        link.clicks += 1
        link.last_clicked_at = datetime.now(timezone.utc)
        await db.commit()

        return RedirectResponse(
            url=add_ml_affiliate_tracking(link.affiliate_url),
            status_code=302,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Redirect-To": link.provider or "affiliate",
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
        "affiliate_url": add_ml_affiliate_tracking(link.affiliate_url),
        "source": link.source,
        "clicks": link.clicks,
        "is_dead": link.is_dead or False,
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
    Se o link estiver marcado como morto (is_dead), redireciona para a home.
    """
    try:
        result = await db.execute(select(ShortLink).where(ShortLink.code == code))
        link = result.scalar()

        if not link:
            return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)

        # Link quebrado — não redireciona para loja morta
        if link.is_dead:
            return RedirectResponse(
                url=f"{settings.PUBLIC_SITE_URL}/oferta/{code}?expired=1",
                status_code=302,
            )

        # Register click
        click = ClickEvent(
            offer_id=str(link.id),
            provider=link.provider,
            product_title=link.product_title,
            price=link.price,
            affiliate_url=link.affiliate_url,
            ip_address=(
                request.headers.get("cf-connecting-ip")
                or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                or (request.client.host if request.client else None)
            ),
            user_agent=request.headers.get("user-agent"),
            referrer=request.headers.get("referer"),
            source=link.source or "video",
        )
        db.add(click)
        link.clicks += 1
        link.last_clicked_at = datetime.now(timezone.utc)
        await db.commit()

        return RedirectResponse(
            url=add_ml_affiliate_tracking(link.affiliate_url),
            status_code=302,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Redirect-To": link.provider or "affiliate",
            }
        )
    except Exception:
        return RedirectResponse(url=settings.PUBLIC_SITE_URL, status_code=302)


@router.post("/r/{code}/report-dead")
async def report_dead_link(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Marca um short link como quebrado (produto removido da loja).
    Usado pelo botão 'Link quebrado?' na página /oferta/{code}.
    """
    from app.core.rate_limit import check_rate_limit, get_client_ip

    ip = get_client_ip(request)
    if not await check_rate_limit(ip, key="links_report_dead", max_calls=10, window_seconds=3600):
        return JSONResponse(status_code=429, content={"error": "Too many reports from this IP."})

    result = await db.execute(select(ShortLink).where(ShortLink.code == code))
    link = result.scalar()

    if not link:
        return JSONResponse(status_code=404, content={"error": "Link not found"})

    if not link.is_dead:
        link.is_dead = True
        link.dead_reported_at = datetime.now(timezone.utc)
        await db.commit()

    return {"ok": True, "code": code, "is_dead": True}


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

        import ipaddress
        import socket

        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as c:
            current_url = original_url
            for _ in range(4):
                if not _is_allowed_image_url(current_url):
                    return Response(status_code=403)

                parsed = urlparse(current_url)
                try:
                    infos = socket.getaddrinfo(parsed.hostname, None)
                except socket.gaierror:
                    return Response(status_code=404)

                for _, _, _, _, sockaddr in infos:
                    try:
                        ip = ipaddress.ip_address(sockaddr[0])
                    except ValueError:
                        continue
                    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                        return Response(status_code=403)

                r = await c.get(current_url)
                if 300 <= r.status_code < 400:
                    location = r.headers.get("location")
                    if not location:
                        return Response(status_code=404)
                    current_url = urljoin(current_url, location)
                    continue
                if r.status_code != 200:
                    return Response(status_code=404)
                if len(r.content) > 10 * 1024 * 1024:
                    return Response(status_code=413)
                break
            else:
                return Response(status_code=400)

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
