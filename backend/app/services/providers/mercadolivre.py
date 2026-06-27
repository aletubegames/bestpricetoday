"""Mercado Livre Provider — busca via API oficial do Mercado Livre.

Fluxo:
  1. Busca produtos no catalogo: /products/search?site_id=MLB&q=...
  2. Para cada produto, busca o item mais barato: /products/{id}/items?limit=1
  3. Mapeia para OfferSchema

Se o token ML nao estiver disponivel ou a API falhar, cai no fallback
local da tabela affiliate_products.
"""
import asyncio
import re
import unicodedata
from typing import List, Optional
import httpx
from app.services.providers.base import BaseProvider
from app.schemas.schemas import OfferSchema, ProviderEnum, ProviderSearchState
from app.core.config import settings
from app.core.logging import logger

_STOPWORDS = {"de", "da", "do", "para", "com", "em", "e", "o", "a", "os", "as", "um", "uma"}


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _tokenize(query: str) -> list[str]:
    tokens = re.findall(r"\w+", _normalize(query))
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _score(title: str, tokens: list[str]) -> float:
    """Proporcao de tokens da query presentes no titulo normalizado."""
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
            self.set_status(
                ProviderSearchState.not_configured,
                message="ML app nao configurado.",
            )
            return []

        # Garante que links de afiliado estejam configurados antes de buscar
        if not settings.ML_AFFILIATE_MATT_WORD or not settings.ML_AFFILIATE_MATT_TOOL:
            self.set_status(
                ProviderSearchState.not_configured,
                message="ML_AFFILIATE_MATT_WORD e ML_AFFILIATE_MATT_TOOL nao configurados.",
            )
            return []

        try:
            # 1. PRIMEIRO busca na tabela affiliate_products (dados do scraper com meli.la)
            offers = await self._local_fallback(query, limit)
            if offers:
                return offers

            # 2. API do ML desativada — retorna URLs longas sem meli.la
            # Só usamos produtos do scraper (com links de afiliado reais)
            self.set_status(
                ProviderSearchState.no_results,
                message="ML nao retornou ofertas. Rode o scraper para atualizar.",
            )
            return []
        except Exception as e:
            logger.error(f"MercadoLivre error: {e}")
            self.set_status(
                ProviderSearchState.error,
                message=f"MercadoLivre error: {e}",
            )
            return []

    async def _get_token(self) -> Optional[str]:
        from app.db.session import AsyncSessionLocal
        from app.services.ml_token_service import get_token
        try:
            async with AsyncSessionLocal() as db:
                return await get_token(db)
        except Exception:
            return None

    async def _search_api(self, query: str, limit: int, token: str) -> List[OfferSchema]:
        async with httpx.AsyncClient(timeout=20) as client:
            # Endpoint /sites/MLB/search foi DESATIVADO pelo ML (403 Forbidden)
            # Usar /products/search (catálogo) + /products/{id}/items (itens)
            # Documentação: https://developers.mercadolivre.com.ar/en_us/categories-and-attributes/products-search
            r = await client.get(
                "https://api.mercadolibre.com/products/search",
                params={"site_id": "MLB", "q": query, "limit": 50, "status": "active"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code != 200:
                self.set_status(
                    ProviderSearchState.error,
                    message=f"ML products/search falhou: HTTP {r.status_code}",
                )
                return []

            products = r.json().get("results", [])
            if not products:
                self.set_status(
                    ProviderSearchState.no_results,
                    message="ML nao retornou produtos para esta busca.",
                )
                return []

            tokens = _tokenize(query)

            # Busca itens em paralelo para cada produto do catálogo
            async def fetch_item(prod: dict) -> Optional[OfferSchema]:
                pid = prod.get("id") or prod.get("catalog_product_id")
                if not pid:
                    return None
                try:
                    # Busca detalhes do produto (imagem)
                    r_prod = await client.get(
                        f"https://api.mercadolibre.com/products/{pid}?includes=items",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    prod_data = r_prod.json() if r_prod.status_code == 200 else {}
                    pictures = prod_data.get("pictures", [])
                    image_url = pictures[0].get("url", "") if pictures else ""

                    # Busca o item com melhor preço
                    r2 = await client.get(
                        f"https://api.mercadolibre.com/products/{pid}/items",
                        params={"limit": 1},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if r2.status_code != 200:
                        logger.warning(f"ML items for {pid}: HTTP {r2.status_code}")
                        return None
                    items = r2.json().get("results", [])
                    if not items:
                        logger.warning(f"ML items for {pid}: no results")
                        return None
                    item = items[0]
                    item_id = item.get("item_id")
                    if not item_id:
                        logger.warning(f"ML items for {pid}: no item_id")
                        return None

                    # Formato oficial do Mercado Livre para produtos:
                    # https://produto.mercadolivre.com.br/MLB-{id}-_JM
                    # Adiciona parametros de afiliado do Programa de Afiliados e Criadores.
                    import re
                    numeric_id = re.sub(r"^MLB", "", item_id)
                    base_url = f"https://produto.mercadolivre.com.br/MLB-{numeric_id}-_JM"
                    if settings.ML_AFFILIATE_MATT_WORD and settings.ML_AFFILIATE_MATT_TOOL:
                        permalink = (
                            f"{base_url}"
                            f"?matt_word={settings.ML_AFFILIATE_MATT_WORD}"
                            f"&matt_tool={settings.ML_AFFILIATE_MATT_TOOL}"
                        )
                    else:
                        permalink = base_url

                    price = item.get("price", 0)
                    original_price = item.get("original_price") or price
                    discount = 0.0
                    if original_price and original_price > price:
                        discount = round((original_price - price) / original_price * 100, 2)
                    shipping = item.get("shipping", {})
                    free_shipping = shipping.get("free_shipping", False)
                    title = item.get("title") or prod.get("name", "")
                    return OfferSchema(
                        provider=ProviderEnum.mercadolivre,
                        title=title,
                        price=price,
                        original_price=original_price,
                        discount_percent=discount,
                        shipping_free=free_shipping,
                        shipping_price=0.0,
                        final_price=price,
                        score=round(_score(title, tokens), 4),
                        product_id=pid,
                        product_url=permalink,
                        affiliate_url=permalink,
                        image_url=image_url,
                        economy=round((original_price or price) - price, 2),
                    )
                except Exception as e:
                    logger.warning(f"ML item fetch failed for {pid}: {e}")
                    return None

            tasks = [fetch_item(p) for p in products[:50]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            offers = [o for o in results if isinstance(o, OfferSchema)]
            logger.info(f"ML search '{query}': {len(products)} produtos no catalogo, {len(offers)} itens validos")

        if not offers:
            self.set_status(
                ProviderSearchState.no_results,
                message="ML encontrou produtos, mas nenhum item com preco disponivel.",
            )
            return []

        self.set_status(
            ProviderSearchState.ok,
            message=f"Mercado Livre: {len(offers)} oferta(s) do catalogo.",
            returned_count=len(offers),
        )
        return offers[:limit]

    async def _local_fallback(self, query: str, limit: int) -> List[OfferSchema]:
        """Busca na tabela affiliate_products quando a API nao esta disponivel."""
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.models import AffiliateProduct
            from sqlalchemy import select, or_, and_, func

            tokens = _tokenize(query)
            q_lower = f"%{_normalize(query)}%"

            async with AsyncSessionLocal() as db:
                if tokens:
                    # AND: todos os tokens devem aparecer no titulo OU categoria OU notes
                    # Isso evita retornar produtos irrelevantes que match apenas 1 token
                    token_filters = [
                        or_(
                            func.lower(AffiliateProduct.title).like(f"%{t}%"),
                            func.lower(AffiliateProduct.category).like(f"%{t}%"),
                            func.lower(AffiliateProduct.notes).like(f"%{t}%"),
                        )
                        for t in tokens
                    ]
                    where_clause = and_(*token_filters)
                else:
                    where_clause = func.lower(AffiliateProduct.title).like(q_lower)

                stmt = (
                    select(AffiliateProduct)
                    .where(
                        AffiliateProduct.is_active == True,
                        AffiliateProduct.title != None,
                        where_clause,
                    )
                    .limit(limit * 3)
                )
                result = await db.execute(stmt)
                products = result.scalars().all()

            if not products:
                self.set_status(
                    ProviderSearchState.no_results,
                    message="Nenhum produto afiliado ML para esta busca.",
                )
                return []

            # Filtra por score minimo (pelo menos 50% dos tokens no titulo)
            min_score = 0.5 if len(tokens) > 1 else 0.0
            scored = sorted(
                products,
                key=lambda p: _score(p.title or "", tokens),
                reverse=True,
            )
            scored = [p for p in scored if _score(p.title or "", tokens) >= min_score][:limit]

            offers = []
            for p in scored:
                price = p.price or 0.01
                s = _score(p.title or "", tokens)
                # Garante que o affiliate_url tenha matt_word + matt_tool (tracking de afiliado ML)
                aff_url = p.affiliate_url or ""
                if aff_url and settings.ML_AFFILIATE_MATT_WORD and settings.ML_AFFILIATE_MATT_TOOL:
                    if "matt_word" not in aff_url:
                        # Remove fragment (#...) e adiciona matt params antes do fragment
                        fragment = ""
                        if "#" in aff_url:
                            aff_url, fragment = aff_url.split("#", 1)
                            fragment = "#" + fragment
                        sep = "&" if "?" in aff_url else "?"
                        # Remove UTMs genéricos se existirem (vão ser re-adicionados pelo add_utm)
                        aff_url = (
                            f"{aff_url}{sep}matt_word={settings.ML_AFFILIATE_MATT_WORD}"
                            f"&matt_tool={settings.ML_AFFILIATE_MATT_TOOL}"
                            f"{fragment}"
                        )
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
                    product_url=aff_url,
                    affiliate_url=aff_url,
                    image_url=p.image_url or "",
                    economy=0.0,
                ))

            self.set_status(
                ProviderSearchState.ok,
                message=f"Mercado Livre: {len(offers)} produto(s) afiliado(s) local.",
                returned_count=len(offers),
            )
            return offers

        except Exception as e:
            self.set_status(ProviderSearchState.error, message=f"Mercado Livre fallback falhou: {e}")
            return []
