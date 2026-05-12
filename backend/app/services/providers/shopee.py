"""Shopee Affiliate Provider."""
import httpx
import time
import hmac
import hashlib
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger


class ShopeeProvider(BaseProvider):
    name = "shopee"
    BASE_URL = "https://open-api.affiliate.shopee.com.br/graphql"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.SHOPEE_APP_ID:
            logger.warning("Shopee: not configured, skipping")
            return []
        try:
            return await self._do_search(query, limit)
        except Exception as e:
            logger.error(f"Shopee error: {e}")
            return []

    async def _do_search(self, query: str, limit: int) -> List[OfferSchema]:
        timestamp = int(time.time())
        payload = {
            "query": """
            query searchProducts($keyword: String!, $limit: Int!) {
              productOfferV2(listType: 0, sortType: 2, limit: $limit, keyword: $keyword) {
                nodes {
                  itemId
                  productName
                  priceMin
                  priceMax
                  imageUrl
                  shopName
                  offerLink
                  commissionRate
                  sales
                }
              }
            }
            """,
            "variables": {"keyword": query, "limit": limit},
        }

        sign_string = f"{settings.SHOPEE_APP_ID}{timestamp}"
        signature = hmac.new(
            settings.SHOPEE_SECRET.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()

        client = await self.get_client()
        resp = await client.post(
            self.BASE_URL,
            json=payload,
            headers={
                "Authorization": f"SHA256 Credential={settings.SHOPEE_APP_ID},Timestamp={timestamp},Signature={signature}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data)

    def _parse(self, data: dict) -> List[OfferSchema]:
        offers = []
        nodes = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
        for item in nodes:
            price = float(item.get("priceMin", 0))
            cashback = float(item.get("commissionRate", 0))
            offers.append(OfferSchema(
                provider=ProviderEnum.shopee,
                title=item.get("productName", ""),
                price=price,
                cashback_percent=cashback,
                shipping_free=True,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("offerLink", ""),
                image_url=item.get("imageUrl", ""),
            ))
        return offers
