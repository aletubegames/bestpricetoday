from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import init_db
from app.api.v1.router import api_router
import sentry_sdk
import time
import uuid


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.DEBUG else "INFO")
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

    yield

    cron_task.cancel()
    broadcast_task.cancel()
    distributor_task.cancel()
    bot_task.cancel()
    alert_task.cancel()
    ml_refresh_task.cancel()
    for task in [cron_task, broadcast_task, distributor_task, bot_task, alert_task, ml_refresh_task]:
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

# Custom CORS middleware - FORCE headers on ALL responses
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Handle OPTIONS preflight
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
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

    # Force CORS headers on ALL responses
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = _CORS_ALLOW_HEADERS

    # Disable cache completely
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

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


app.include_router(api_router, prefix=settings.API_V1_STR)
# qua 13 mai 2026 19:21:05 -03

# dom 17 mai 2026 23:24:52 -03
# deploy auth 1779081470
