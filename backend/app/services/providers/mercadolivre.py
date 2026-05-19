"""Mercado Livre Provider — usa /products/search (disponível com OAuth user token).

/sites/MLB/search está bloqueado por policy do app.
Fluxo: /products/search → lista catálogo → /products/{id} para buy_box_winner (preço).
Link afiliado: https://www.mercadolivre.com.br/p/{id}?matt_tool={APP_ID}
"""
import asyncio
from typing import List, Optional
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger


class MercadoLivreProvider(BaseProvider):
    name = "mercadolivre"
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self):
        super().__init__()

    async def _get_token(self) -> Optional[str]:
        try:
            from app.db.session import AsyncSessionLocal
            from app.services.ml_token_service import get_token as get_db_token
            async with AsyncSessionLocal() as db:
                token = await get_db_token(db)
                if token:
                    return token
        except Exception as e:
            logger.error(f"ML _get_token DB lookup failed: {type(e).__name__}: {e}")
        if settings.MERCADOLIVRE_ACCESS_TOKEN:
            return settings.MERCADOLIVRE_ACCESS_TOKEN
        return None

    def _affiliate_url(self, catalog_product_id: str) -> str:
        return f"https://www.mercadolivre.com.br/p/{catalog_product_id}?matt_tool={settings.MERCADOLIVRE_APP_ID}"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.MERCADOLIVRE_APP_ID:
            self.set_status(ProviderSearchState.not_configured, message="MERCADOLIVRE_APP_ID não configurado.")
            return []

        token = await self._get_token()
        if not token:
            self.set_status(ProviderSearchState.error, message="Sem token ML. Faça OAuth via /auth/ml/authorize.")
            return []

        try:
            client = await self.get_client()
            headers = {"Authorization": f"Bearer {token}"}

            # Busca catálogo
            r = await client.get(
                f"{self.BASE_URL}/products/search",
                params={"site_id": "MLB", "q": query, "limit": min(limit * 2, 20)},
                headers=headers,
            )

            if r.status_code == 401:
                self.set_status(ProviderSearchState.error, message="Token ML expirado. Renove via /auth/ml/authorize.", http_status=401)
                return []

            if r.status_code != 200:
                self.set_status(ProviderSearchState.error, message=f"ML /products/search retornou {r.status_code}.", http_status=r.status_code)
                return []

            products = r.json().get("results", [])
            if not products:
                self.set_status(ProviderSearchState.no_results, message="ML não encontrou produtos para esta busca.", http_status=200)
                return []

            # Busca detalhes em paralelo (buy_box_winner + imagem)
            offers = await self._parse_products(products[:limit], headers)

            self.set_status(
                ProviderSearchState.ok if offers else ProviderSearchState.no_results,
                message=f"Mercado Livre retornou {len(offers)} ofertas." if offers else "ML retornou produtos mas sem preço disponível.",
                http_status=200,
                raw_count=len(products),
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Mercado Livre falhou: {e}")
            logger.error(f"MercadoLivreProvider search error: {e}")
            return []

    async def _parse_products(self, products: list, headers: dict) -> List[OfferSchema]:
        tasks = [self._fetch_offer(p, headers) for p in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, OfferSchema)]

    async def _fetch_offer(self, product: dict, headers: dict) -> Optional[OfferSchema]:
        try:
            pid = product.get("id") or product.get("catalog_product_id")
            if not pid:
                return None

            client = await self.get_client()
            r = await client.get(
                f"{self.BASE_URL}/products/{pid}",
                params={"includes": "buy_box_winner"},
                headers=headers,
            )

            if r.status_code != 200:
                return None

            data = r.json()
            bb = data.get("buy_box_winner") or {}
            price = float(bb.get("price") or 0)

            # Imagem
            pictures = data.get("pictures") or product.get("pictures") or []
            image = pictures[0].get("url", "").replace("-F.jpg", "-O.jpg") if pictures else ""

            # Nome
            name = data.get("name") or product.get("name") or ""
            if not name:
                return None

            affiliate_url = self._affiliate_url(pid)

            return OfferSchema(
                provider=ProviderEnum.mercadolivre,
                title=name,
                price=price if price else 0.0,
                original_price=price if price else 0.0,
                discount_percent=0.0,
                shipping_free=bb.get("free_shipping", False),
                shipping_price=0.0,
                final_price=price if price else 0.0,
                affiliate_url=affiliate_url,
                image_url=image,
                economy=0.0,
            )
        except Exception as e:
            logger.debug(f"ML _fetch_offer error for {product.get('id')}: {e}")
            return None
