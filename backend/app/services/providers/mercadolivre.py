"""Mercado Livre Provider — busca na tabela local affiliate_products.

A API ML não funciona sem OAuth válido e as políticas do app restringem
o uso de /sites/MLB/search. A abordagem adotada é:
  1. Buscar na tabela affiliate_products os produtos cujo título/código
     contém a query (ILIKE), ordenando por relevância simples.
  2. Retornar como OfferSchema com o link de afiliado real do produto.
  3. Isso garante que todos os links são afiliados válidos do proprietário.
"""
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings


class MercadoLivreProvider(BaseProvider):
    name = "mercadolivre"

    def __init__(self):
        super().__init__()

    async def search(self, query: str, limit: int = 10) -> List[OfferSchema]:
        if not settings.MERCADOLIVRE_APP_ID:
            self.set_status(ProviderSearchState.not_configured, message="ML não configurado.")
            return []

        try:
            from app.db.session import AsyncSessionLocal
            from app.models.models import AffiliateProduct
            from sqlalchemy import select, or_, func

            q_lower = f"%{query.lower()}%"

            async with AsyncSessionLocal() as db:
                stmt = (
                    select(AffiliateProduct)
                    .where(
                        AffiliateProduct.is_active == True,
                        AffiliateProduct.title != None,
                        or_(
                            func.lower(AffiliateProduct.title).like(q_lower),
                            func.lower(AffiliateProduct.category).like(q_lower),
                            func.lower(AffiliateProduct.notes).like(q_lower),
                        )
                    )
                    .limit(limit)
                )
                result = await db.execute(stmt)
                products = result.scalars().all()

            if not products:
                self.set_status(ProviderSearchState.no_results,
                                message="Nenhum produto afiliado ML encontrado para esta busca.")
                return []

            offers = []
            for p in products:
                price = p.price or 0.01
                offers.append(OfferSchema(
                    provider=ProviderEnum.mercadolivre,
                    title=p.title or p.ml_code or "",
                    price=price,
                    original_price=price,
                    discount_percent=0.0,
                    shipping_free=True,
                    shipping_price=0.0,
                    final_price=price,
                    score=0.0,
                    product_id=p.ml_code,
                    product_url=p.affiliate_url,
                    affiliate_url=p.affiliate_url,
                    image_url=p.image_url or "",
                    economy=0.0,
                ))

            self.set_status(
                ProviderSearchState.ok,
                message=f"Mercado Livre retornou {len(offers)} produtos afiliados.",
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Mercado Livre falhou: {e}")
            return []
