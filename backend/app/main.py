from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.session import init_db
from app.api.v1.router import api_router
import sentry_sdk
import time


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

    # Start Telegram channel broadcaster
    from app.workers.channel_broadcaster import run_broadcaster_loop
    broadcast_task = asyncio.create_task(run_broadcaster_loop())

    # Start Telegram bot polling
    from app.workers.bestprice_bot import start_bot_polling
    bot_task = asyncio.create_task(start_bot_polling())

    # Start price alert checker
    from app.workers.alert_checker import run_checker_loop
    alert_task = asyncio.create_task(run_checker_loop())

    yield

    cron_task.cancel()
    broadcast_task.cancel()
    bot_task.cancel()
    alert_task.cancel()
    for task in [cron_task, broadcast_task, bot_task, alert_task]:
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("BestPriceToday shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000)
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


app.include_router(api_router, prefix=settings.API_V1_STR)
# qua 13 mai 2026 19:21:05 -03

# dom 17 mai 2026 23:24:52 -03
