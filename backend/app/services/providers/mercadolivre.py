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
        try:
            token = await self._get_token()
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/products/search",
                params={"site_id": "MLB", "q": query, "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_results(data.get("results", []))
        except Exception as e:
            logger.error(f"MercadoLivre search failed: {e}")
            return []

    def _parse_results(self, results: list) -> List[OfferSchema]:
        offers = []
        for item in results:
            buy_box = item.get("buy_box_winner", {})
            price = float(buy_box.get("price") or item.get("price") or 0)
            if not price:
                continue
            original = float(buy_box.get("original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            free_shipping = buy_box.get("shipping", {}).get("free_shipping", False)
            shipping_cost = 0 if free_shipping else 15.0
            pid = item.get("id", "")
            pictures = item.get("pictures", [])
            image = pictures[0].get("url", "") if pictures else ""
            offers.append(OfferSchema(
                provider=ProviderEnum.mercadolivre,
                title=item.get("name", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=free_shipping,
                shipping_price=shipping_cost,
                final_price=price + shipping_cost,
                affiliate_url=self._build_affiliate_url(f"https://www.mercadolivre.com.br/p/{pid}"),
                image_url=image,
                economy=original - price if original > price else 0,
            ))
        return offers
