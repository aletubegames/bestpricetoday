"""
Redirect endpoint — tracked affiliate links.
GET /r/{code} → register click + 302 redirect to affiliate URL
POST /links/create → create a new short link, returns the code
"""
from fastapi import APIRouter, Depends, Request
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
            source=data.source,
            campaign=data.campaign,
        )
        db.add(link)
        await db.commit()

        return {
            "code": code,
            "url": f"https://bestpricetoday.vercel.app/r/{code}",
            "short_url": f"https://bestpricetoday.vercel.app/r/{code}",
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
    Tracked redirect.
    1. Find link by code
    2. Register click (ClickEvent)
    3. Update link stats
    4. 302 redirect to affiliate URL
    """
    try:
        result = await db.execute(select(ShortLink).where(ShortLink.code == code))
        link = result.scalar()

        if not link:
            # Fallback to homepage
            return RedirectResponse(url="https://bestpricetoday.vercel.app", status_code=302)

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

        # Update link stats
        link.clicks += 1
        link.last_clicked_at = datetime.now(timezone.utc)

        await db.commit()

        # 302 redirect — immediate, no intermediate page
        return RedirectResponse(
            url=link.affiliate_url,
            status_code=302,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Redirect-To": link.provider or "affiliate",
            }
        )

    except Exception:
        # Always redirect even on error
        return RedirectResponse(url="https://bestpricetoday.vercel.app", status_code=302)
