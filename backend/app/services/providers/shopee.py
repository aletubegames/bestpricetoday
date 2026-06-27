"""
Shopee Provider — ponte entre a camada de integração e o orquestrador de busca.

Usa ShopeeClient (integrations/shopee) para todas as chamadas.
Converte ProductResult → OfferSchema.
"""
from typing import List

from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.integrations.shopee import ShopeeClient
from app.integrations.base import ProductResult
from app.core.logging import logger


class ShopeeProvider(BaseProvider):
    name = "shopee"

    def __init__(self) -> None:
        super().__init__()
        self._client = ShopeeClient()

    def _to_offer(self, p: ProductResult) -> OfferSchema:
        from app.core.config import settings
        return OfferSchema(
            provider=ProviderEnum.shopee,
            title=p.title,
            price=p.price,
            original_price=p.original_price,
            discount_percent=p.discount_pct,
            coupon_code=p.coupon_code,
            coupon_discount=p.coupon_discount,
            cashback_percent=p.cashback_pct,
            shipping_free=p.shipping_free,
            shipping_price=p.shipping_price,
            final_price=p.final_price,
            product_id=p.external_id,
            product_url=p.product_url,
            affiliate_url=p.affiliate_url or "",
            tracking_id=str(settings.SHOPEE_AFFILIATE_ID) if settings.SHOPEE_AFFILIATE_ID else None,
            image_url=p.image_url,
            economy=p.economy,
            is_fake_discount=False,
        )

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        from app.core.config import settings

        if not settings.SHOPEE_APP_ID or not settings.SHOPEE_SECRET:
            self.set_status(
                ProviderSearchState.not_configured,
                message="Credenciais Shopee (APP_ID/SECRET) não configuradas.",
            )
            return []

        try:
            results = await self._client.search(query, limit=limit)

            if not results:
                self.set_status(
                    ProviderSearchState.no_results,
                    message="Shopee não retornou produtos para esta busca.",
                )
                return []

            offers = [self._to_offer(p) for p in results]
            self.set_status(
                ProviderSearchState.ok,
                message=f"Shopee retornou {len(offers)} ofertas.",
                raw_count=len(offers),
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(
                ProviderSearchState.error,
                message=f"Shopee falhou: {e}",
            )
            logger.error(f"ShopeeProvider error: {e}")
            return []

    async def close(self) -> None:
        await self._client.close()
