"""AliExpress Portals Affiliate Provider."""
import httpx
import time
import hmac
import hashlib
import json
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger


class AliExpressProvider(BaseProvider):
    name = "aliexpress"
    BASE_URL = "https://api-sg.aliexpress.com/sync"
    METHOD = "aliexpress.affiliate.product.query"

    def _sign_request(self, params: dict) -> str:
        sorted_params = sorted(params.items())
        sign_str = settings.ALIEXPRESS_APP_SECRET + "".join(f"{k}{v}" for k, v in sorted_params) + settings.ALIEXPRESS_APP_SECRET
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.ALIEXPRESS_APP_KEY:
            logger.warning("AliExpress: not configured, skipping")
            return []
        try:
            return await self._do_search(query, limit)
        except Exception as e:
            logger.error(f"AliExpress error: {e}")
            return []

    async def _do_search(self, query: str, limit: int) -> List[OfferSchema]:
        timestamp = str(int(time.time() * 1000))
        params = {
            "app_key": settings.ALIEXPRESS_APP_KEY,
            "method": self.METHOD,
            "timestamp": timestamp,
            "sign_method": "md5",
            "tracking_id": settings.ALIEXPRESS_TRACKING_ID,
            "keywords": query,
            "page_size": str(min(limit, 50)),
            "page_no": "1",
            "sort": "SALE_PRICE_ASC",
            "target_currency": "BRL",
            "target_language": "PT",
            "ship_to_country": "BR",
        }
        params["sign"] = self._sign_request(params)

        client = await self.get_client()
        resp = await client.post(self.BASE_URL, data=params)
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data)

    def _parse(self, data: dict) -> List[OfferSchema]:
        offers = []
        result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
        if result.get("resp_code") != 200:
            return []
        products = result.get("result", {}).get("products", {}).get("product", [])
        for item in products:
            price = float(item.get("target_sale_price", 0))
            original = float(item.get("target_original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            offers.append(OfferSchema(
                provider=ProviderEnum.aliexpress,
                title=item.get("product_title", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=item.get("ship_to_days", "") == "0",
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("promotion_link", item.get("product_detail_url", "")),
                image_url=item.get("product_main_image_url", ""),
                economy=original - price if original > price else 0,
            ))
        return offers
