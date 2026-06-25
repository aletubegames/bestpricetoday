"""Awin Affiliate Provider."""
import httpx
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger


class AwinProvider(BaseProvider):
    name = "awin"
    BASE_URL = "https://api.awin.com"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.AWIN_API_TOKEN or not settings.AWIN_PUBLISHER_ID:
            logger.warning("Awin: not configured, skipping")
            self.set_status(
                ProviderSearchState.not_configured,
                message="Credenciais Awin (API_TOKEN/PUBLISHER_ID) não configuradas.",
            )
            return []
        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/publishers/{settings.AWIN_PUBLISHER_ID}/product-feeds",
                headers={"Authorization": f"Bearer {settings.AWIN_API_TOKEN}"},
                params={"keyword": query, "countryCode": "BR", "pageSize": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            logger.error(f"Awin error: {e}")
            return []

    def _parse(self, data) -> List[OfferSchema]:
        offers = []
        items = data if isinstance(data, list) else data.get("data", [])
        for item in items:
            price = float(item.get("displayPrice") or item.get("price", {}).get("amount", 0))
            offers.append(OfferSchema(
                provider=ProviderEnum.awin,
                title=item.get("productName", ""),
                price=price,
                shipping_free=False,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("aw_deep_link", item.get("url", "")),
                image_url=item.get("image_url", ""),
            ))
        return offers
