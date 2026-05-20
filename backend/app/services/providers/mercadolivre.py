"""Mercado Livre Provider — busca na tabela local affiliate_products.

Fluxo:
  query → tokeniza → ILIKE em title/category/notes → score por relevância → OfferSchema
Sem chamada externa. Todos os links são afiliados reais do proprietário.
"""
import re
import unicodedata
from typing import List
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings

_STOPWORDS = {"de", "da", "do", "para", "com", "em", "e", "o", "a", "os", "as", "um", "uma"}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokenize(query: str) -> list[str]:
    tokens = re.findall(r"\w+", _normalize(query))
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _score(title: str, tokens: list[str]) -> float:
    """Proporção de tokens da query presentes no título normalizado."""
    if not tokens:
        return 1.0
    norm = _normalize(title)
    hits = sum(1 for t in tokens if t in norm)
    return hits / len(tokens)


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
            from sqlalchemy import select, or_, and_, func

            tokens  = _tokenize(query)
            q_lower = f"%{_normalize(query)}%"

            async with AsyncSessionLocal() as db:
                # Busca ampla: qualquer token presente em title/category/notes
                if tokens:
                    token_filters = [
                        or_(
                            func.lower(AffiliateProduct.title).like(f"%{t}%"),
                            func.lower(AffiliateProduct.category).like(f"%{t}%"),
                            func.lower(AffiliateProduct.notes).like(f"%{t}%"),
                        )
                        for t in tokens
                    ]
                    # OR entre tokens (inclusivo) para não retornar vazio
                    where_clause = or_(*token_filters)
                else:
                    where_clause = func.lower(AffiliateProduct.title).like(q_lower)

                stmt = (
                    select(AffiliateProduct)
                    .where(
                        AffiliateProduct.is_active == True,
                        AffiliateProduct.title != None,
                        where_clause,
                    )
                    .limit(limit * 3)  # busca mais, filtra por score depois
                )
                result   = await db.execute(stmt)
                products = result.scalars().all()

            if not products:
                self.set_status(ProviderSearchState.no_results,
                                message="Nenhum produto afiliado ML para esta busca.")
                return []

            # Calcular score e ordenar
            scored = sorted(
                products,
                key=lambda p: _score(p.title or "", tokens),
                reverse=True,
            )[:limit]

            offers = []
            for p in scored:
                price = p.price or 0.01
                s     = _score(p.title or "", tokens)
                offers.append(OfferSchema(
                    provider=ProviderEnum.mercadolivre,
                    title=p.title or p.ml_code or "",
                    price=price,
                    original_price=price,
                    discount_percent=0.0,
                    shipping_free=True,
                    shipping_price=0.0,
                    final_price=price,
                    score=round(s, 4),
                    product_id=p.ml_code,
                    product_url=p.affiliate_url,
                    affiliate_url=p.affiliate_url,
                    image_url=p.image_url or "",
                    economy=0.0,
                ))

            self.set_status(
                ProviderSearchState.ok,
                message=f"Mercado Livre: {len(offers)} produto(s) afiliado(s).",
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Mercado Livre falhou: {e}")
            return []
