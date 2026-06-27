"""
AliExpress Provider — ponte entre a camada de integração e o orquestrador de busca.

Usa AliExpressClient (integrations/aliexpress) para todas as chamadas.
Converte ProductResult → OfferSchema.
"""
from typing import List

from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.integrations.aliexpress import AliExpressClient
from app.integrations.base import ProductResult
from app.core.logging import logger


class AliExpressProvider(BaseProvider):
    name = "aliexpress"

    def __init__(self) -> None:
        super().__init__()
        self._client = AliExpressClient()

    def _to_offer(self, p: ProductResult) -> OfferSchema:
        from app.core.config import settings
        import re
        # Extrai product_id do product_url se external_id estiver vazio
        pid = p.external_id
        if not pid and p.product_url:
            m = re.search(r"/item/(\d+)\.html", p.product_url)
            if m:
                pid = m.group(1)
        return OfferSchema(
            provider=ProviderEnum.aliexpress,
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
            product_id=pid,
            product_url=p.product_url,
            affiliate_url=p.affiliate_url or "",
            tracking_id=settings.ALIEXPRESS_TRACKING_ID,
            image_url=p.image_url,
            economy=p.economy,
            is_fake_discount=p.discount_pct > 80,
        )

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        from app.core.config import settings

        if not settings.ALIEXPRESS_APP_KEY or not settings.ALIEXPRESS_APP_SECRET:
            self.set_status(
                ProviderSearchState.not_configured,
                message="Credenciais AliExpress (APP_KEY/APP_SECRET) não configuradas.",
            )
            return []
        if not settings.ALIEXPRESS_TRACKING_ID:
            self.set_status(
                ProviderSearchState.not_configured,
                message="ALIEXPRESS_TRACKING_ID não configurado — links não seriam afiliados.",
            )
            return []

        try:
            results = await self._client.search(query, limit=limit)

            if not results:
                self.set_status(
                    ProviderSearchState.no_results,
                    message="AliExpress não retornou produtos relevantes para esta busca.",
                )
                return []

            offers = [self._to_offer(p) for p in results]
            self.set_status(
                ProviderSearchState.ok,
                message=f"AliExpress retornou {len(offers)} ofertas relevantes.",
                raw_count=len(offers),
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(
                ProviderSearchState.error,
                message=f"AliExpress falhou: {e}",
            )
            logger.error(f"AliExpressProvider error: {e}")
            return []

    async def close(self) -> None:
        await self._client.close()
