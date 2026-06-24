"""
Camada base de integração para marketplaces afiliados.

Cada marketplace herda MarketplaceClient e implementa:
  - search(query, limit) → List[ProductResult]
  - get_affiliate_link(url) → str
  - get_coupons(store) → List[CouponResult]       (opcional)
  - get_hot_products(limit) → List[ProductResult] (opcional)

A camada de providers (services/providers/*.py) consome esses clients
e converte para OfferSchema.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

import httpx

from app.core.logging import logger


# ─────────────────────────────────────────────
# Tipos comuns
# ─────────────────────────────────────────────

class MarketplaceId(str, Enum):
    aliexpress = "aliexpress"
    shopee     = "shopee"
    amazon     = "amazon"
    mercadolivre = "mercadolivre"
    kabum      = "kabum"
    magalu     = "magalu"


@dataclass
class ProductResult:
    """Produto normalizado retornado por qualquer marketplace."""
    marketplace:     MarketplaceId
    external_id:     str
    title:           str
    price:           float
    original_price:  Optional[float]    = None
    discount_pct:    float              = 0.0
    currency:        str                = "BRL"
    image_url:       Optional[str]      = None
    product_url:     Optional[str]      = None
    affiliate_url:   Optional[str]      = None
    shipping_free:   bool               = False
    shipping_price:  float              = 0.0
    cashback_pct:    float              = 0.0
    coupon_code:     Optional[str]      = None
    coupon_discount: float              = 0.0
    sales_count:     Optional[int]      = None
    rating:          Optional[float]    = None
    category_id:     Optional[str]      = None
    extra:           dict               = field(default_factory=dict)

    @property
    def final_price(self) -> float:
        effective = self.price - self.coupon_discount
        return round(max(effective, 0.0) + self.shipping_price, 2)

    @property
    def economy(self) -> float:
        if self.original_price and self.original_price > self.price:
            return round(self.original_price - self.price, 2)
        return 0.0


@dataclass
class CouponResult:
    marketplace:    MarketplaceId
    code:           str
    description:    str
    discount_type:  str    = "percent"   # "percent" | "fixed"
    discount_value: float  = 0.0
    min_purchase:   float  = 0.0
    store:          str    = ""
    valid_until:    Optional[str] = None


# ─────────────────────────────────────────────
# Interface base
# ─────────────────────────────────────────────

class MarketplaceClient(ABC):
    """
    Cliente base para integrações de marketplace.

    Subclasses devem definir:
      - marketplace_id: MarketplaceId
    E implementar:
      - search()
      - get_affiliate_link()
    """
    marketplace_id: MarketplaceId
    timeout: int = 10
    max_retries: int = 3

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "BestPriceToday/2.0"},
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[ProductResult]:
        """Busca produtos pelo termo. Retorna lista normalizada."""

    @abstractmethod
    async def get_affiliate_link(self, product_url: str, **kwargs) -> str:
        """Gera link de afiliado rastreado para a URL do produto."""

    async def get_coupons(self, store: str = "") -> List[CouponResult]:
        """Retorna cupons disponíveis. Override opcional."""
        return []

    async def get_hot_products(self, limit: int = 10) -> List[ProductResult]:
        """Retorna produtos em destaque/hot. Override opcional."""
        return []

    async def safe_search(self, query: str, limit: int = 10) -> List[ProductResult]:
        """search() com retry automático e tratamento de exceções."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                return await self.search(query, limit)
            except httpx.TimeoutException as e:
                last_exc = e
                logger.warning(
                    f"{self.marketplace_id}: timeout (attempt {attempt + 1}/{self.max_retries})"
                )
            except Exception as e:
                last_exc = e
                logger.error(
                    f"{self.marketplace_id}: error on attempt {attempt + 1}: {e}"
                )
            if attempt < self.max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
        logger.error(f"{self.marketplace_id}: all retries exhausted. Last error: {last_exc}")
        return []
