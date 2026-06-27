from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BestPriceToday"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # NÃO use o valor default em produção. Defina SECRET_KEY no .env
    SECRET_KEY: str = "change-me-in-production"

    @property
    def secret_key_validated(self) -> str:
        if self.SECRET_KEY == "change-me-in-production":
            import warnings
            warnings.warn(
                "SECRET_KEY is using the insecure default value. "
                "Set SECRET_KEY in your .env file.",
                RuntimeWarning, stacklevel=2,
            )
        return self.SECRET_KEY
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

    # Affiliate link parameters (Programa de Afiliados e Criadores do Mercado Livre)
    ML_AFFILIATE_MATT_WORD: str = ""
    ML_AFFILIATE_MATT_TOOL: str = ""
    # NOTE: ML_WEBHOOK_SECRET removed (2026-06-26) — ML affiliate program
    # does not provide webhooks for affiliates. Conversions tracked via scraping.
    ML_TOKEN_ENCRYPTION_KEY: str = ""  # Optional AES-256 key material for DB token encryption

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
    TELEGRAM_CHANNEL_ID: str = ""  # @BestPriceTodayor -1001234567890

    # Sentry
    SENTRY_DSN: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://bestpricetoday.alaserver.com.br",
        "https://bestpricetoday.alaserver.com.br:9443",
        "https://bestpricetoday.com.br",
    ]

    ADMIN_MANAGER_KEY: str = ""

    # TikTok API
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REDIRECT_URI: str = os.getenv("TIKTOK_REDIRECT_URI", "https://api.alaserver.com.br:9443/api/v1/tiktok/callback")

    # YouTube
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = os.getenv("YOUTUBE_REDIRECT_URI", "https://api.alaserver.com.br:9443/api/v1/aletube/callback/youtube")

    # Instagram / Facebook
    INSTAGRAM_APP_ID: str = ""  # Legacy - use ID_APLICATIVO_INSTAGRAM
    INSTAGRAM_APP_SECRET: str = ""  # Legacy - use SECRET_KEY_INSTAGRAM_APP
    ID_APLICATIVO_INSTAGRAM: str = ""
    SECRET_KEY_INSTAGRAM_APP: str = ""
    ID_APLICATIVO_FACEBOOK: str = ""
    FACEBOOK_APP_SECRET: str = ""  # Para validar signed requests do Data Deletion Callback
    FACEBOOK_PAGE_ACCESS_TOKEN: str = ""
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI", "https://api.alaserver.com.br:9443/api/v1/aletube/callback/facebook")

    # Claude API (para análise de vídeo) — direto, opcional
    ANTHROPIC_API_KEY: str = ""

    # OpenRouter (proxy multi-modelo) — preferido para análise IA com vision
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL:   str = "anthropic/claude-3.5-sonnet"

    # Video API (GPU local via ngrok ou URL fixa)
    VIDEO_API_URL: str = "https://sacrament-subduing-confined.ngrok-free.dev"
    VIDEO_API_KEY: str = ""

    # URL interna usada por workers para se comunicar com a própria API
    # Em produção: https://api.alaserver.com.br:9443 (nginx proxy para backend na 8000)
    INTERNAL_API_URL: str = "https://api.alaserver.com.br:9443"

    # URL pública do frontend (usada em short links, mensagens Telegram, etc.)
    # Em produção: https://bestpricetoday.alaserver.com.br:9443 (nginx proxy para frontend na 3000)
    PUBLIC_SITE_URL: str = "https://bestpricetoday.alaserver.com.br:9443"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        # Le variaveis de ambiente do sistema (HF Spaces secrets)
        extra = "ignore"


settings = Settings()
# force restart 1779071296
# updated 1779072514
