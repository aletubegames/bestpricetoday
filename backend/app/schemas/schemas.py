from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ProviderEnum(str, Enum):
    mercadolivre = "mercadolivre"
    amazon = "amazon"
    shopee = "shopee"
    kabum = "kabum"
    aliexpress = "aliexpress"
    awin = "awin"
    lomadee = "lomadee"


class ProviderSearchState(str, Enum):
    ok = "ok"
    no_results = "no_results"
    not_configured = "not_configured"
    blocked = "blocked"
    low_relevance = "low_relevance"
    error = "error"


class OfferSchema(BaseModel):
    provider: ProviderEnum
    title: str
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: float = 0
    coupon_code: Optional[str] = None
    coupon_discount: float = 0
    cashback_percent: float = 0
    shipping_price: float = 0
    shipping_free: bool = False
    final_price: Optional[float] = None
    score: float = 0
    product_id: Optional[str] = None
    product_url: Optional[str] = None
    affiliate_url: Optional[str] = None
    tracking_id: Optional[str] = None
    image_url: Optional[str] = None
    is_fake_discount: bool = False
    economy: float = 0

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    limit: int = Field(default=20, ge=1, le=50)
    providers: Optional[List[ProviderEnum]] = None


class ProviderStatusSchema(BaseModel):
    provider: ProviderEnum
    status: ProviderSearchState
    message: Optional[str] = None
    http_status: Optional[int] = None
    raw_count: int = 0
    returned_count: int = 0
    filtered_count: int = 0


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    total: int
    offers: List[OfferSchema]
    provider_statuses: List[ProviderStatusSchema] = Field(default_factory=list)
    search_id: Optional[UUID] = None
    cached: bool = False
    took_ms: int = 0


class PriceHistoryPoint(BaseModel):
    price: float
    provider: ProviderEnum
    recorded_at: datetime


class AlertCreate(BaseModel):
    query: str
    target_price: float
    product_id: Optional[UUID] = None
    telegram_id: Optional[str] = None  # para alertas anônimos via Telegram


class AlertResponse(BaseModel):
    id: UUID
    query: str
    target_price: float
    is_active: bool
    telegram_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClickTrack(BaseModel):
    offer_id: UUID
    provider: ProviderEnum


# --- Favoritos ---

class FavoriteCreate(BaseModel):
    product_id: UUID


class FavoriteResponse(BaseModel):
    id: UUID
    product_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# --- Analytics ---

class ClickTrackResponse(BaseModel):
    ok: bool
    click_id: UUID
