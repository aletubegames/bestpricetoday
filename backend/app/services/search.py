"""Main search orchestrator — parallel provider queries."""
import asyncio
import random
import time
from collections import Counter
from typing import List, Optional
# Providers ativos
from app.services.providers.mercadolivre import MercadoLivreProvider
from app.services.providers.amazon import AmazonProvider
from app.services.providers.shopee import ShopeeProvider
from app.services.providers.aliexpress import AliExpressProvider
from app.services.providers.lomadee import LomadeeProvider
from app.services.providers.base import add_utm
# Pendente:
# from app.services.providers.kabum import KabumProvider
# from app.services.providers.awin import AwinProvider
from app.services.ranking.engine import rank_offers
from app.schemas.schemas import OfferSchema, SearchResponse, ProviderEnum, ProviderSearchState, ProviderStatusSchema
from app.core.cache import get_cached, set_cached, make_cache_key, get_redis
from app.core.logging import logger
from app.integrations.aliexpress import AliExpressClient
from app.integrations.shopee import ShopeeClient
import unicodedata
import re


TRENDING_SEARCHES_KEY = "search:trending"
TRENDING_SEARCHES_LABELS_KEY = "search:trending:labels"
TRENDING_SEARCHES_MAX_ITEMS = 200
TRENDING_DISCOVERY_CACHE_TTL = 15 * 60
fallback_trending_scores: Counter[str] = Counter()
fallback_trending_labels: dict[str, str] = {}


def normalize_query(query: str) -> str:
    query = query.lower().strip()
    query = unicodedata.normalize("NFKD", query)
    query = "".join(c for c in query if not unicodedata.combining(c))
    query = re.sub(r"\s+", " ", query)
    return query


def clean_display_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def trim_trending_label(query: str, max_length: int = 64) -> str:
    cleaned = clean_display_query(query)
    if len(cleaned) <= max_length:
        return cleaned
    truncated = cleaned[: max_length - 1].rsplit(" ", 1)[0]
    return truncated or cleaned[:max_length]


def merge_trending_items(*sources: list[dict[str, int | str]]) -> list[dict[str, int | str]]:
    merged: dict[str, dict[str, int | str]] = {}

    for source in sources:
        for item in source:
            query = trim_trending_label(str(item["query"]))
            normalized_query = normalize_query(query)
            if len(normalized_query) < 2:
                continue

            score = int(item.get("score", 1))
            existing = merged.get(normalized_query)
            if existing is None or score > int(existing["score"]):
                merged[normalized_query] = {"query": query, "score": score}

    return list(merged.values())


async def record_trending_query(query: str) -> None:
    display_query = trim_trending_label(query)
    normalized_query = normalize_query(display_query)
    if len(normalized_query) < 2:
        return

    fallback_trending_scores[normalized_query] += 1
    fallback_trending_labels[normalized_query] = display_query

    try:
        redis = await get_redis()
        await redis.zincrby(TRENDING_SEARCHES_KEY, 1, normalized_query)
        await redis.hset(TRENDING_SEARCHES_LABELS_KEY, normalized_query, display_query)
        await redis.zremrangebyrank(TRENDING_SEARCHES_KEY, 0, -(TRENDING_SEARCHES_MAX_ITEMS + 1))
    except Exception as exc:
        logger.warning(f"Redis unavailable for trending write: {exc}")


async def fetch_live_trending_queries(limit: int = 40) -> list[dict[str, int | str]]:
    cache_key = make_cache_key("trending_live", limit=limit)
    cached = await get_cached(cache_key)
    if cached:
        return cached

    clients = [AliExpressClient(), ShopeeClient()]
    tasks = [client.get_hot_products(limit=limit) for client in clients]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        live_items: list[dict[str, int | str]] = []

        for source_index, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Trending discovery source failed: {result}")
                continue

            weight = max(limit - source_index, 1)
            for rank, product in enumerate(result):
                label = trim_trending_label(product.title)
                if len(label) < 2:
                    continue
                live_items.append({
                    "query": label,
                    "score": max(weight - rank, 1),
                })

        deduped_items = merge_trending_items(live_items)
        await set_cached(cache_key, deduped_items, ttl=TRENDING_DISCOVERY_CACHE_TTL)
        return deduped_items
    finally:
        await asyncio.gather(*[client.close() for client in clients], return_exceptions=True)


async def get_trending_searches(limit: int = 8) -> list[dict[str, int | str]]:
    if limit <= 0:
        return []

    recent_items: list[dict[str, int | str]] = []
    try:
        redis = await get_redis()
        top_queries = await redis.zrevrange(TRENDING_SEARCHES_KEY, 0, limit - 1, withscores=True)
        if top_queries:
            normalized_queries = [query for query, _ in top_queries]
            display_queries = await redis.hmget(TRENDING_SEARCHES_LABELS_KEY, normalized_queries)
            recent_items = [
                {
                    "query": trim_trending_label(display_query or normalized_query),
                    "score": int(score),
                }
                for (normalized_query, score), display_query in zip(top_queries, display_queries)
            ]
    except Exception as exc:
        logger.warning(f"Redis unavailable for trending read: {exc}")

    if not recent_items:
        most_common = fallback_trending_scores.most_common(limit * 2)
        recent_items = [
            {
                "query": trim_trending_label(fallback_trending_labels.get(normalized_query, normalized_query)),
                "score": score,
            }
            for normalized_query, score in most_common
        ]

    live_items = await fetch_live_trending_queries(limit=max(limit * 2, 20))
    merged_items = merge_trending_items(recent_items, live_items)
    random.shuffle(merged_items)

    boosted_recent_queries = {normalize_query(str(item["query"])) for item in recent_items}
    merged_items.sort(
        key=lambda item: (
            normalize_query(str(item["query"])) not in boosted_recent_queries,
            -int(item["score"]),
        )
    )

    selected_items = merged_items[:limit * 2]
    random.shuffle(selected_items)
    return selected_items[:limit]


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
    provider_key = ",".join(sorted([p.value for p in providers])) if providers else "all"
    cache_key = make_cache_key("search", query=normalized, limit=limit, providers=provider_key)

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
            tasks.append(instance.safe_search(normalized, limit=min(limit, 30)))

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

    ranked = rank_offers(all_offers, query=normalized)

    # Garantir diversidade de providers nos resultados
    # (produtos da Amazon/ML podem ter score baixo por preço alto,
    #  mas são links afiliados reais com comissão)
    providers_with_offers = {}
    for o in ranked:
        p = o.provider.value
        if p not in providers_with_offers:
            providers_with_offers[p] = []
        if len(providers_with_offers[p]) < 3:  # max 3 por provider
            providers_with_offers[p].append(o)

    # Round-robin: intercala ofertas de cada provider
    merged = []
    max_per_provider = {p: 3 for p in providers_with_offers}
    provider_queues = {p: list(offers) for p, offers in providers_with_offers.items()}
    while len(merged) < limit:
        added = False
        # Prioriza Amazon e ML (comissão real), depois outros
        priority = ["amazon", "mercadolivre", "shopee", "aliexpress", "lomadee", "kabum", "awin"]
        sorted_providers = [p for p in priority if p in provider_queues] + \
                          [p for p in provider_queues if p not in priority]
        for p in sorted_providers:
            if provider_queues[p] and max_per_provider.get(p, 3) > 0:
                merged.append(provider_queues[p].pop(0))
                max_per_provider[p] -= 1
                added = True
                if len(merged) >= limit:
                    break
        if not added:
            break

    ranked = merged[:limit] if merged else ranked[:limit]

    # Add UTM params to all affiliate links
    for offer in ranked:
        if offer.affiliate_url:
            offer.affiliate_url = add_utm(offer.affiliate_url, offer.provider)

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
    await record_trending_query(query)
    return response
