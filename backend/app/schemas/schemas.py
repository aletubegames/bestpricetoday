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


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    total: int
    offers: List[OfferSchema]
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


class AlertResponse(BaseModel):
    id: UUID
    query: str
    target_price: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClickTrack(BaseModel):
    offer_id: UUID
    provider: ProviderEnum
