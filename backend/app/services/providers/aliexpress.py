"""AliExpress Portals Affiliate Provider.

Sem App Key: gera links de afiliado via deep link do portal.
Com App Key (Open Platform): usa API completa.
"""
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
    PORTAL_SEARCH = "https://portals.aliexpress.com/appPortal/api/affiliate/product/query"

    def _sign_request(self, params: dict) -> str:
        sorted_params = sorted(params.items())
        sign_str = settings.ALIEXPRESS_APP_SECRET + "".join(f"{k}{v}" for k, v in sorted_params) + settings.ALIEXPRESS_APP_SECRET
        return hashlib.md5(sign_str.encode()).hexdigest().upper()

    def _build_affiliate_link(self, product_id: str) -> str:
        tracking = settings.ALIEXPRESS_TRACKING_ID or "bestpricetoday"
        return f"https://s.click.aliexpress.com/e/_oFnMhD7?bz={product_id}&dl=https%3A%2F%2Fwww.aliexpress.com%2Fitem%2F{product_id}.html&aff_fcid={tracking}"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if settings.ALIEXPRESS_APP_KEY:
            try:
                return await self._search_api(query, limit)
            except Exception as e:
                logger.error(f"AliExpress API error: {e}")
        # Fallback: busca via portal sem autenticacao
        return await self._search_portal(query, limit)

    async def _search_portal(self, query: str, limit: int) -> List[OfferSchema]:
        """Busca via portal de afiliados (sem app_key)."""
        try:
            client = await self.get_client()
            resp = await client.get(
                self.PORTAL_SEARCH,
                params={
                    "keywords": query,
                    "pageSize": min(limit, 20),
                    "pageNo": 1,
                    "currency": "BRL",
                    "country": "BR",
                    "language": "PT",
                    "trackingId": settings.ALIEXPRESS_TRACKING_ID or "bestpricetoday",
                },
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                    "Referer": "https://portals.aliexpress.com",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("result", {}).get("productList", data.get("data", {}).get("products", []))
                if products:
                    return self._parse_portal(products)
        except Exception as e:
            logger.error(f"AliExpress portal error: {e}")

        # Sem API key e portal falhou — não retorna lixo
        logger.warning("AliExpress: sem credenciais e portal indisponível, skipping")
        return []

    def _parse_portal(self, products: list) -> List[OfferSchema]:
        offers = []
        for item in products:
            price = float(item.get("salePrice", item.get("originalPrice", 0)) or 0)
            original = float(item.get("originalPrice", price) or price)
            discount = round((1 - price / original) * 100, 1) if original > price and price > 0 else 0
            pid = str(item.get("productId", ""))
            offers.append(OfferSchema(
                provider=ProviderEnum.aliexpress,
                title=item.get("productTitle", item.get("title", "")),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=True,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("promotionLink", self._build_affiliate_link(pid)),
                image_url=item.get("imageUrl", item.get("productMainImageUrl", "")),
                economy=original - price if original > price else 0,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=False,
            ))
        return offers

    async def _search_api(self, query: str, limit: int) -> List[OfferSchema]:
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
        return self._parse_api(data)

    def _parse_api(self, data: dict) -> List[OfferSchema]:
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
                shipping_free=True,
                shipping_price=0,
                final_price=price,
                affiliate_url=item.get("promotion_link", item.get("product_detail_url", "")),
                image_url=item.get("product_main_image_url", ""),
                economy=original - price if original > price else 0,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=False,
            ))
        return offers
