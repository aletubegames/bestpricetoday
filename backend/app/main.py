from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import init_db
from app.api.v1.router import api_router
from app.core.visitor_tracking import track_visitor
import sentry_sdk
import os
import time
import asyncio
from collections import defaultdict


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.DEBUG else "INFO")
    settings.validate_runtime()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
    await init_db()
    logger.info("BestPriceToday started")
    # Start conversion cron
    import asyncio
    from app.workers.conversion_cron import start_conversion_cron
    cron_task = asyncio.create_task(start_conversion_cron())

    # Start Telegram channel broadcaster (legacy — desativado, substituído pelo distributor)
    # from app.workers.channel_broadcaster import run_broadcaster_loop
    # broadcast_task = asyncio.create_task(run_broadcaster_loop())
    broadcast_task = asyncio.ensure_future(asyncio.sleep(0))  # no-op placeholder

    # Start distributor (orquestrador central — Telegram com IA + filtros de qualidade)
    from app.workers.distributor import run_distributor_loop
    distributor_task = asyncio.create_task(run_distributor_loop())

    # Start Telegram bot polling
    from app.workers.bestprice_bot import start_bot_polling
    bot_task = asyncio.create_task(start_bot_polling())

    # Start price alert checker
    from app.workers.alert_checker import run_checker_loop
    alert_task = asyncio.create_task(run_checker_loop())

    # Start ML token auto-refresh (a cada 25 min)
    from app.workers.ml_refresh_cron import start_ml_refresh_cron
    ml_refresh_task = asyncio.create_task(start_ml_refresh_cron())

    # Start coupon distributor (2x/dia — separado do distributor principal)
    from app.workers.coupon_distributor import coupon_distributor_loop
    coupon_task = asyncio.create_task(coupon_distributor_loop())

    # Resumo semanal pro dono (segunda ~9h) — métricas reais do PLANO_RENDA §4
    from app.workers.weekly_report import run_weekly_report_loop
    report_task = asyncio.create_task(run_weekly_report_loop())

    yield

    cron_task.cancel()
    broadcast_task.cancel()
    distributor_task.cancel()
    bot_task.cancel()
    alert_task.cancel()
    ml_refresh_task.cancel()
    coupon_task.cancel()
    report_task.cancel()
    for task in [cron_task, broadcast_task, distributor_task, bot_task, alert_task, ml_refresh_task, coupon_task, report_task]:
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("BestPriceToday shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    # /docs e /redoc desabilitados em prod — habilitados apenas com DEBUG=True
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

_CORS_ALLOW_HEADERS = (
    "Content-Type, Authorization, X-Requested-With, Accept, Origin, "
    "X-Admin-Key, X-Api-Key, X-Auth-Token, ngrok-skip-browser-warning"
)

# ── CORS whitelist ───────────────────────────────────────────────────────────
# Só origins do BestPriceToday (e localhost para dev) podem chamar a API
# do browser. Chamadas server-side (curl, httpx, Instagram Graph API) não
# enviam Origin header e não são afetadas por CORS.
_ALLOWED_CORS_HOSTS = {
    "bestpricetoday.alaserver.com.br",
    "api.alaserver.com.br",
    "localhost",
}


def _cors_origin_ok(origin: str | None) -> bool:
    """True se o Origin está na whitelist de hosts permitidos."""
    if not origin:
        return False
    from urllib.parse import urlparse
    try:
        host = urlparse(origin).hostname or ""
        return host in _ALLOWED_CORS_HOSTS
    except Exception:
        return False


# Rate limiting simples (não afeta funcionamento normal, apenas protege contra abuso)
_rate_limit_store = defaultdict(list)
_RATE_LIMIT = 240  # requisições por minuto por IP
_RATE_WINDOW = 60  # segundos

# Custom CORS middleware - FORCE headers on ALL responses
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Rate limiting simples (não afeta uso normal, apenas protege contra abuso)
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Limpa requisições antigas
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] 
        if now - ts < _RATE_WINDOW
    ]
    
    # Verifica se excedeu o limite
    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return Response(status_code=429, content="Too many requests")
    
    # Registra a requisição
    _rate_limit_store[client_ip].append(now)
    
    # Origin do request — só setamos CORS headers se for permitido
    origin = request.headers.get("origin")
    allow_origin = origin if _cors_origin_ok(origin) else None

    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        if not allow_origin:
            return Response(status_code=403, content="Origin not allowed")
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = _CORS_ALLOW_HEADERS
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    try:
        response = await call_next(request)
    except Exception:
        response = Response(status_code=500)

    # CORS headers só se origin for permitida
    if allow_origin:
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = _CORS_ALLOW_HEADERS

    # Disable cache completely
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # Security headers (não afetam funcionamento, apenas hardening)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Registra visitante online (usado pelo admin / Online Agora)
    # roda fora do fluxo crítico para não atrasar resposta
    asyncio.create_task(track_visitor(request))

    return response

# app.add_middleware(GZipMiddleware, minimum_size=1024)  # Temporarily disabled for CORS


# class SecurityHeadersMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         response = await call_next(request)
#         response.headers["X-Content-Type-Options"] = "nosniff"
#         response.headers["X-Frame-Options"] = "DENY"
#         response.headers["X-XSS-Protection"] = "1; mode=block"
#         response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
#         return response


# app.add_middleware(SecurityHeadersMiddleware)  # Temporarily disabled for CORS


# @app.middleware("http")
# async def add_request_id(request: Request, call_next):
#     request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
#     request.state.request_id = request_id
#     response = await call_next(request)
#     response.headers["X-Request-ID"] = request_id
#     return response


# @app.middleware("http")
# async def add_timing(request: Request, call_next):
#     start = time.time()
#     response = await call_next(request)
#     duration = round((time.time() - start) * 1000)
#     response.headers["X-Response-Time"] = f"{duration}ms"
#     return response


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/health/ready")
async def readiness():
    checks = {"database": "error", "redis": "degraded"}
    try:
        from sqlalchemy import text
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error(f"Readiness database check failed: {type(exc).__name__}")

    try:
        from app.core.cache import get_redis

        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning(f"Readiness Redis check degraded: {type(exc).__name__}")

    ready = checks["database"] == "ok"
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "version": settings.APP_VERSION,
            "checks": checks,
        },
    )


# Mount static files directory for test videos and other assets
# __file__ is /home/alessandro/backend/app/main.py, so we go up one level to backend/static
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files mounted at /static from {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")


app.include_router(api_router, prefix=settings.API_V1_STR)
# qua 13 mai 2026 19:21:05 -03

# dom 17 mai 2026 23:24:52 -03
# deploy auth 1779081470
