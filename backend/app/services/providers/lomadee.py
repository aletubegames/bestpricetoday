"""Lomadee Affiliate Provider (aggregates many Brazilian stores)."""
import httpx
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger


class LomadeeProvider(BaseProvider):
    name = "lomadee"
    BASE_URL = "https://api.lomadee.com/v3"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.LOMADEE_SOURCE_ID:
            logger.warning("Lomadee: not configured, skipping")
            return []
        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/{settings.LOMADEE_SOURCE_ID}/offer/_search",
                params={
                    "keyword": query,
                    "size": limit,
                    "page": 1,
                    "sort": "price_asc",
                    "token": settings.LOMADEE_APP_TOKEN,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            logger.error(f"Lomadee error: {e}")
            return []

    def _parse(self, data: dict) -> List[OfferSchema]:
        offers = []
        for item in data.get("offers", []):
            price = float(item.get("price", 0))
            original = float(item.get("priceFrom") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            offers.append(OfferSchema(
                provider=ProviderEnum.lomadee,
                title=item.get("name", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=False,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("link", ""),
                image_url=item.get("thumbnail", ""),
                economy=original - price if original > price else 0,
            ))
        return offers
