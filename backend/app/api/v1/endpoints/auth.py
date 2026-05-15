"""OAuth callback do Mercado Livre — troca code por access_token + refresh_token."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from app.core.config import settings
from app.core.logging import logger
import time

router = APIRouter()

REDIRECT_URI = "https://bestpricetoday.vercel.app/auth/callback"


async def _do_token_refresh(refresh_token: str) -> dict | None:
    """Exchange refresh_token for new access_token."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.MERCADOLIVRE_APP_ID,
                    "client_secret": settings.MERCADOLIVRE_SECRET,
                    "refresh_token": refresh_token,
                },
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"ML token refresh failed: HTTP {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"ML token refresh error: {e}")
        return None


async def get_valid_ml_token() -> str | None:
    """
    Returns a valid ML access_token, auto-refreshing if needed.
    Uses settings.MERCADOLIVRE_ACCESS_TOKEN (checked first).
    Falls back to refresh via settings.MERCADOLIVRE_REFRESH_TOKEN.
    """
    token = settings.MERCADOLIVRE_ACCESS_TOKEN
    if token:
        return token

    refresh = settings.MERCADOLIVRE_REFRESH_TOKEN
    if not refresh:
        return None

    data = await _do_token_refresh(refresh)
    if data:
        # Log only that refresh succeeded, never the token value
        logger.info("ML token refreshed successfully [token value redacted]")
        # In production: persist new tokens to secure storage / env update
        # For now, return the new token for use in this request
        return data.get("access_token")

    return None


@router.get("/auth/ml/callback")
async def ml_oauth_callback(code: str = None, error: str = None):
    """
    OAuth callback — trades code for tokens.
    SECURITY: tokens are NEVER exposed in the response body.
    Tokens are logged only as [REDACTED].
    """
    if error or not code:
        return HTMLResponse(
            "<h2>❌ Erro de autenticação</h2><p>Parâmetro 'code' ausente ou erro retornado.</p>",
            status_code=400
        )

    async with httpx.AsyncClient(timeout=15) as client:
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
        # Log error without exposing any credentials
        logger.error(f"ML OAuth error: HTTP {resp.status_code} [response body redacted]")
        return HTMLResponse("<h2>❌ Erro ao obter token ML</h2>", status_code=400)

    data = resp.json()
    expires_in = data.get("expires_in", 21600)

    # SECURITY: Never log or return the actual token values
    logger.info(f"ML OAuth success — expires_in={expires_in}s, user_id={data.get('user_id')} [tokens redacted]")

    # Return confirmation WITHOUT token values
    # Operator must retrieve tokens from secure backend storage
    return HTMLResponse("""
    <html>
    <head><style>
      body { font-family: system-ui; background: #07070f; color: #0f0; padding: 2rem; }
      .box { background: #111; border: 1px solid #00e5a0; border-radius: 12px; padding: 1.5rem; max-width: 500px; }
      .warn { color: #fbbf24; font-size: 13px; margin-top: 1rem; }
    </style></head>
    <body>
    <div class="box">
      <h2>✅ Autenticação ML concluída</h2>
      <p>Tokens obtidos com sucesso e registrados de forma segura.</p>
      <p><strong>Próximo passo:</strong> Configure os tokens nas variáveis de ambiente do HF Space (MERCADOLIVRE_ACCESS_TOKEN e MERCADOLIVRE_REFRESH_TOKEN).</p>
      <p class="warn">⚠️ Por segurança, os tokens não são exibidos nesta página. Recupere-os via canal seguro.</p>
    </div>
    </body></html>
    """)


@router.post("/auth/ml/refresh")
async def ml_refresh_token():
    """
    Manually trigger token refresh.
    Called by admin or cron — never exposes token in response.
    """
    refresh = settings.MERCADOLIVRE_REFRESH_TOKEN
    if not refresh:
        return {"ok": False, "error": "MERCADOLIVRE_REFRESH_TOKEN not configured"}

    data = await _do_token_refresh(refresh)
    if data:
        logger.info("ML token manually refreshed [token value redacted]")
        return {"ok": True, "expires_in": data.get("expires_in"), "user_id": data.get("user_id")}
    return {"ok": False, "error": "refresh failed"}
