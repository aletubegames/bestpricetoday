"""Mercado Livre Affiliates Provider."""
import httpx
from typing import List, Optional
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
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
        if not settings.MERCADOLIVRE_ACCESS_TOKEN and not (settings.MERCADOLIVRE_APP_ID and settings.MERCADOLIVRE_SECRET):
            self.set_status(
                ProviderSearchState.not_configured,
                message="Credenciais do Mercado Livre não configuradas.",
            )
            return []
        try:
            token = settings.MERCADOLIVRE_ACCESS_TOKEN or await self._get_token()
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/sites/MLB/search",
                params={"q": query, "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 403:
                self.set_status(
                    ProviderSearchState.blocked,
                    message="Mercado Livre bloqueou a busca desta aplicação (403).",
                    http_status=403,
                )
                logger.warning("MercadoLivre: acesso bloqueado (app novo). Aguardando liberação.")
                return []
            resp.raise_for_status()
            data = resp.json()
            raw_results = data.get("results", [])
            offers = self._parse_results(raw_results)
            self.set_status(
                ProviderSearchState.ok if offers else ProviderSearchState.no_results,
                message=(
                    f"Mercado Livre retornou {len(offers)} ofertas."
                    if offers
                    else "Mercado Livre respondeu sem resultados para esta busca."
                ),
                http_status=resp.status_code,
                raw_count=len(raw_results),
                returned_count=len(offers),
            )
            return offers
        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Mercado Livre falhou: {e}")
            logger.error(f"MercadoLivre search failed: {e}")
            return []

    def _parse_results(self, results: list) -> List[OfferSchema]:
        offers = []
        for item in results:
            price = float(item.get("price") or 0)
            if not price:
                continue
            original = float(item.get("original_price") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            free_shipping = item.get("shipping", {}).get("free_shipping", False)
            shipping_cost = 0 if free_shipping else 15.0
            permalink = item.get("permalink", "")
            image = item.get("thumbnail", "").replace("I.jpg", "O.jpg")  # imagem maior
            offers.append(OfferSchema(
                provider=ProviderEnum.mercadolivre,
                title=item.get("title", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=free_shipping,
                shipping_price=shipping_cost,
                final_price=price + shipping_cost,
                affiliate_url=self._build_affiliate_url(permalink),
                image_url=image,
                economy=original - price if original > price else 0,
            ))
        return offers
