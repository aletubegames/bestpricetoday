"""OAuth callback do Mercado Livre — troca code por access_token + refresh_token."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import httpx
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()

REDIRECT_URI = "https://bestpricetoday.vercel.app/auth/callback"


@router.get("/auth/ml/callback")
async def ml_oauth_callback(code: str = None, error: str = None):
    if error or not code:
        return HTMLResponse(f"<h2>Erro: {error or 'code ausente'}</h2>", status_code=400)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.MERCADOLIVRE_APP_ID,
                "client_secret": settings.MERCADOLIVRE_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
        )

    if resp.status_code != 200:
        logger.error(f"ML OAuth error: {resp.text}")
        return HTMLResponse(f"<h2>Erro ML: {resp.text}</h2>", status_code=400)

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in")

    logger.info(f"ML OAuth OK — expires_in={expires_in}")

    return HTMLResponse(f"""
    <html><body style="font-family:monospace;padding:2rem;background:#111;color:#0f0">
    <h2>✅ ML OAuth OK</h2>
    <p><b>access_token:</b><br><textarea rows=3 cols=80>{access_token}</textarea></p>
    <p><b>refresh_token:</b><br><textarea rows=3 cols=80>{refresh_token}</textarea></p>
    <p><b>expires_in:</b> {expires_in}s</p>
    <hr>
    <p>Copie o <b>refresh_token</b> e cole no <code>.env</code> como <code>MERCADOLIVRE_REFRESH_TOKEN</code>.<br>
    Copie o <b>access_token</b> como <code>MERCADOLIVRE_ACCESS_TOKEN</code>.</p>
    </body></html>
    """)
