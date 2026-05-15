from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BestPriceToday"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/bestpricetoday"

    # Redis (Upstash)
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 300  # 5 minutes

    # Affiliate APIs
    MERCADOLIVRE_APP_ID: str = ""
    MERCADOLIVRE_SECRET: str = ""
    MERCADOLIVRE_ACCESS_TOKEN: str = ""
    MERCADOLIVRE_REFRESH_TOKEN: str = ""
    MERCADOLIVRE_TOKEN_EXPIRES_AT: int = 0  # Unix timestamp

    AMAZON_ACCESS_KEY: str = ""
    AMAZON_SECRET_KEY: str = ""
    AMAZON_PARTNER_TAG: str = ""
    AMAZON_REGION: str = "br"

    AWIN_PUBLISHER_ID: str = ""
    AWIN_API_TOKEN: str = ""

    LOMADEE_API_KEY: str = ""
    LOMADEE_SOURCE_ID: str = "6ff2699e-ceaa-4fad-a58a-8b91f885485f"

    SHOPEE_APP_ID: str = ""
    SHOPEE_SECRET: str = ""
    SHOPEE_AFFILIATE_ID: str = ""

    KABUM_AFFILIATE_TOKEN: str = ""

    ALIEXPRESS_APP_KEY: str = ""
    ALIEXPRESS_APP_SECRET: str = ""
    ALIEXPRESS_TRACKING_ID: str = ""

    CUPONOMIA_API_KEY: str = ""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""  # @BestPriceTodayBR or -1001234567890

    # Sentry
    SENTRY_DSN: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://bestpricetoday.vercel.app",
        "https://bestpricetoday.com.br",
    ]

    ADMIN_MANAGER_KEY: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Le variaveis de ambiente do sistema (HF Spaces secrets)
        extra = "ignore"


settings = Settings()
