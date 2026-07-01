"""KaBuM Affiliate Provider."""
import httpx
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger


class KabumProvider(BaseProvider):
    name = "kabum"
    BASE_URL = "https://api.kabum.com.br/produtos/busca"

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.KABUM_AFFILIATE_TOKEN:
            self.set_status(
                ProviderSearchState.not_configured,
                message="KABUM_AFFILIATE_TOKEN não configurado — links não seriam afiliados.",
            )
            return []
        try:
            client = await self.get_client()
            resp = await client.get(
                self.BASE_URL,
                params={
                    "string_busca": query,
                    "limite": limit,
                    "pagina": 1,
                    "sort": "menor_preco",
                },
                headers={
                    "Accept": "application/json",
                    "app-token": settings.KABUM_AFFILIATE_TOKEN or "",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data, query)
        except Exception as e:
            logger.error(f"KaBuM error: {e}")
            return []

    def _parse(self, data: dict, query: str) -> List[OfferSchema]:
        offers = []
        products = data.get("data", data.get("produtos", []))
        for item in products:
            price = float(item.get("vlr_oferta") or item.get("preco_desconto") or item.get("preco", 0))
            original = float(item.get("preco") or price)
            discount = round((1 - price / original) * 100, 1) if original > price else 0
            code = item.get("codigo", "")
            aff_token = f"?utm_source=affiliate&utm_medium={settings.KABUM_AFFILIATE_TOKEN}" if settings.KABUM_AFFILIATE_TOKEN else ""
            offers.append(OfferSchema(
                provider=ProviderEnum.kabum,
                title=item.get("nome", ""),
                price=price,
                original_price=original,
                discount_percent=discount,
                shipping_free=False,
                shipping_price=0,
                final_price=price,
                affiliate_url=f"https://www.kabum.com.br/produto/{code}{aff_token}",
                image_url=item.get("imagem", ""),
                economy=original - price if original > price else 0,
            ))
        return offers
