"""Main search orchestrator — parallel provider queries."""
import asyncio
import time
from typing import List, Optional
# Providers ativos
from app.services.providers.mercadolivre import MercadoLivreProvider
from app.services.providers.amazon import AmazonProvider
from app.services.providers.shopee import ShopeeProvider
from app.services.providers.aliexpress import AliExpressProvider
from app.services.providers.lomadee import LomadeeProvider
# Pendente:
# from app.services.providers.kabum import KabumProvider
# from app.services.providers.awin import AwinProvider
from app.services.ranking.engine import rank_offers
from app.schemas.schemas import OfferSchema, SearchResponse, ProviderEnum, ProviderSearchState, ProviderStatusSchema
from app.core.cache import get_cached, set_cached, make_cache_key
from app.core.logging import logger
import unicodedata
import re


def normalize_query(query: str) -> str:
    query = query.lower().strip()
    query = unicodedata.normalize("NFKD", query)
    query = "".join(c for c in query if not unicodedata.combining(c))
    query = re.sub(r"\s+", " ", query)
    return query


# Providers ativos
PROVIDERS = {
    ProviderEnum.mercadolivre: MercadoLivreProvider,
    ProviderEnum.amazon: AmazonProvider,
    ProviderEnum.shopee: ShopeeProvider,
    ProviderEnum.aliexpress: AliExpressProvider,
    ProviderEnum.lomadee: LomadeeProvider,
    # ProviderEnum.kabum: KabumProvider,
    # ProviderEnum.awin: AwinProvider,
}


def _fallback_status(instance, result) -> ProviderStatusSchema:
    if isinstance(result, list) and result:
        return ProviderStatusSchema(
            provider=ProviderEnum(instance.name),
            status=ProviderSearchState.ok,
            message=f"{len(result)} ofertas retornadas.",
            raw_count=len(result),
            returned_count=len(result),
        )

    if isinstance(result, list):
        return ProviderStatusSchema(
            provider=ProviderEnum(instance.name),
            status=ProviderSearchState.no_results,
            message="Nenhum resultado retornado por este provider.",
        )

    return ProviderStatusSchema(
        provider=ProviderEnum(instance.name),
        status=ProviderSearchState.error,
        message=f"Erro interno ao consultar {instance.name}: {result}",
    )


async def search_all(
    query: str,
    limit: int = 20,
    providers: Optional[List[ProviderEnum]] = None,
) -> SearchResponse:
    start = time.time()
    normalized = normalize_query(query)
    cache_key = make_cache_key("search", query=normalized, limit=limit)

    cached = await get_cached(cache_key)
    if cached:
        resp = SearchResponse(**cached)
        resp.cached = True
        return resp

    active_providers = providers or list(PROVIDERS.keys())

    tasks = []
    instances = []
    for p in active_providers:
        if p in PROVIDERS:
            instance = PROVIDERS[p]()
            instances.append(instance)
            tasks.append(instance.safe_search(normalized, limit=min(limit, 10)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_offers: List[OfferSchema] = []
    provider_statuses: List[ProviderStatusSchema] = []
    for instance, result in zip(instances, results):
        if isinstance(result, list):
            all_offers.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Provider error: {result}")
            if instance.last_status is None:
                instance.set_status(
                    ProviderSearchState.error,
                    message=f"Erro interno ao consultar {instance.name}: {result}",
                )

        provider_statuses.append(instance.last_status or _fallback_status(instance, result))

    # Close all clients
    await asyncio.gather(*[i.close() for i in instances], return_exceptions=True)

    ranked = rank_offers(all_offers)[:limit]
    took_ms = int((time.time() - start) * 1000)

    response = SearchResponse(
        query=query,
        normalized_query=normalized,
        total=len(ranked),
        offers=ranked,
        provider_statuses=provider_statuses,
        cached=False,
        took_ms=took_ms,
    )

    await set_cached(cache_key, response.model_dump())
    return response
