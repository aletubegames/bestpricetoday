"""Lomadee Affiliate Provider — API Beta v2
Docs: https://docs.lomadee.com.br
Base: https://api-beta.lomadee.com.br/affiliate

Fluxo correto:
1. GET /affiliate/products?search=query  -> lista produtos
2. POST /affiliate/shortener/url         -> gera link afiliado rastreado
3. Usa link rastreado no botão "Ver oferta"
"""
import httpx
from typing import List, Optional
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum
from app.core.config import settings
from app.core.logging import logger
import asyncio


class LomadeeProvider(BaseProvider):
    name = "lomadee"
    BASE_URL = "https://api-beta.lomadee.com.br/affiliate"
    CHANNEL_ID = "6ff2699e-ceaa-4fad-a58a-8b91f885485f"

    async def _generate_affiliate_link(self, product_url: str, campaign_id: Optional[str] = None) -> Optional[str]:
        """Gera link afiliado rastreado via POST /affiliate/shortener/url"""
        if not product_url:
            return None
        try:
            client = await self.get_client()
            payload = {"url": product_url}
            if campaign_id:
                payload["featureId"] = campaign_id
            resp = await client.post(
                f"{self.BASE_URL}/shortener/url",
                json=payload,
                headers={"x-api-key": settings.LOMADEE_API_KEY},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Retorna shortUrl ou url do response
                short = (data.get("data") or {}).get("shortUrl") or data.get("shortUrl") or data.get("url")
                return short
        except Exception as e:
            logger.error(f"Lomadee shortener error: {e}")
        return None

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.LOMADEE_API_KEY:
            logger.warning("Lomadee: LOMADEE_API_KEY not configured, skipping")
            return []
        try:
            client = await self.get_client()
            resp = await client.get(
                f"{self.BASE_URL}/products",
                params={
                    "search": query,
                    "limit": min(limit, 20),
                    "page": 1,
                    "isAvailable": True,
                },
                headers={"x-api-key": settings.LOMADEE_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            products = data.get("data", [])

            # Gera links afiliados em paralelo (max 5 por vez)
            offers = await self._parse_with_links(products[:limit])
            return [o for o in offers if o.price]
        except Exception as e:
            logger.error(f"Lomadee search error: {e}")
            return []

    async def _parse_with_links(self, products: list) -> List[OfferSchema]:
        """Parse produtos e gera links afiliados em paralelo."""
        tasks = [self._parse_product(item) for item in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        offers = []
        for r in results:
            if isinstance(r, OfferSchema):
                offers.append(r)
        return offers

    async def _parse_product(self, item: dict) -> Optional[OfferSchema]:
        try:
            if not item.get("available", True):
                return None

            # Melhor opção disponível
            options = item.get("options", [])
            best_opt = None
            best_price = float("inf")
            for opt in options:
                if not opt.get("available", True):
                    continue
                pricing = opt.get("pricing", [])
                if pricing:
                    p = pricing[0].get("price", 0)
                    if p and p < best_price:
                        best_price = p
                        best_opt = opt

            if not best_opt and options:
                best_opt = options[0]

            # Preço em centavos -> reais
            pricing = (best_opt or {}).get("pricing", [{}])
            price_cents = pricing[0].get("price", 0) if pricing else 0
            list_cents = pricing[0].get("listPrice", price_cents) if pricing else price_cents
            price = round(price_cents / 100, 2) if price_cents else None
            list_price = round(list_cents / 100, 2) if list_cents else None

            if not price:
                return None

            discount = 0
            economy = 0
            if list_price and list_price > price:
                discount = round((1 - price / list_price) * 100, 1)
                economy = round(list_price - price, 2)

            # Imagem
            images = item.get("images", []) or (best_opt or {}).get("images", [])
            image_url = images[0].get("url", "") if images else ""

            # URL do produto
            product_url = item.get("url", "")

            # Gera link afiliado rastreado
            affiliate_url = await self._generate_affiliate_link(product_url)
            if not affiliate_url:
                affiliate_url = product_url  # fallback para URL direta

            return OfferSchema(
                provider=ProviderEnum.lomadee,
                title=item.get("name", ""),
                price=price,
                original_price=list_price,
                discount_percent=discount,
                shipping_free=False,
                shipping_price=0,
                final_price=price,
                product_id=str(item.get("id", "")),
                product_url=product_url,
                affiliate_url=affiliate_url,
                tracking_id=self.CHANNEL_ID,
                image_url=image_url,
                economy=economy,
                coupon_discount=0,
                cashback_percent=0,
                is_fake_discount=discount > 80,
            )
        except Exception as e:
            logger.error(f"Lomadee parse product error: {e}")
            return None
