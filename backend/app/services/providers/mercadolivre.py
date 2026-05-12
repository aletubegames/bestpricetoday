"""Mercado Livre Affiliates Provider."""
import httpx
from typing import List, Optional
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger
import time


class MercadoLivreProvider(BaseProvider):
    name = "mercadolivre"
    BASE_URL = "https://api.mercadolibre.com"
    AUTH_URL = "https://api.mercadolibre.com/oauth/token"

    def __init__(self):
        super().__init__()
        self._token: Optional[str] = None
        self._token_expires: float = 0

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        client = await self.get_client()
        resp = await client.post(self.AUTH_URL, data={
            "grant_type": "client_credentials",
            "client_id": settings.MERCADOLIVRE_APP_ID,
            "client_secret": settings.MERCADOLIVRE_SECRET,
        })
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data.get("expires_in", 21600)
        return self._token

    def _build_affiliate_url(self, product_url: str) -> str:
        return f"{product_url}?matt_tool={settings.MERCADOLIVRE_APP_ID}"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.MERCADOLIVRE_APP_ID:
            logger.warning("MercadoLivre: APP_ID not configured, using public API")
            return await self._search_public(query, limit)
        try:
            token = await self._get_token()
            return await self._search_authenticated(query, limit, token)
        except Exception as e:
            logger.error(f"MercadoLivre auth failed: {e}, falling back to public")
            return await self._search_public(query, limit)

    async def _search_public(self, query: str, limit: int) -> List[OfferSchema]:
        client = await self.get_client()
        resp = await client.get(
            f"{self.BASE_URL}/sites/MLB/search",
            params={"q": query, "limit": limit, "sort": "price_asc"},
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_results(data.get("results", []))

    async def _search_authenticated(self, query: str, limit: int, token: str) -> List[OfferSchema]:
        client = await self.get_client()
        resp = await client.get(
            f"{self.BASE_URL}/sites/MLB/search",
            params={"q": query, "limit": limit, "sort": "price_asc"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_results(data.get("results", []))

    def _parse_results(self, results: list) -> List[OfferSchema]:
        offers = []
        for item in results:
            price = float(item.get("price", 0))
            original = float(item.get("original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            shipping = item.get("shipping", {})
            free_shipping = shipping.get("free_shipping", False)
            shipping_cost = 0 if free_shipping else 15.0

            offers.append(OfferSchema(
                provider=ProviderEnum.mercadolivre,
                title=item.get("title", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=free_shipping,
                shipping_price=shipping_cost,
                final_price=price + shipping_cost,
                affiliate_url=self._build_affiliate_url(item.get("permalink", "")),
                image_url=item.get("thumbnail", "").replace("I.jpg", "O.jpg"),
                economy=original - price if original > price else 0,
            ))
        return offers
