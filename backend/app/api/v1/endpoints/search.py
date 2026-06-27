from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from app.schemas.schemas import SearchRequest, SearchResponse, TrendingSearchResponse, TrendingSearchItem
from app.services.search import get_trending_searches, search_all
from app.core.logging import logger

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, req: Request):
    from app.core.rate_limit import check_rate_limit
    from fastapi.responses import JSONResponse
    ip = req.client.host if req.client else "unknown"
    if not await check_rate_limit(ip, key="search", max_calls=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit: max 30 buscas/min por IP.")
    try:
        return await search_all(
            query=request.query,
            limit=request.limit,
            providers=request.providers,
        )
    except Exception as e:
        logger.error(f"Search POST error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search", response_model=SearchResponse)
async def search_get(
    req: Request,
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    providers: Optional[str] = Query(default=None, description="Filtrar providers: mercadolivre,shopee,aliexpress,lomadee"),
):
    from app.core.rate_limit import check_rate_limit, get_client_ip
    from app.schemas.schemas import ProviderEnum
    ip = get_client_ip(req)
    if not await check_rate_limit(ip, key="search", max_calls=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit: max 30 buscas/min por IP.")
    try:
        provider_list = None
        if providers:
            provider_list = [ProviderEnum(p.strip()) for p in providers.split(",") if p.strip()]
        return await search_all(query=q, limit=limit, providers=provider_list)
    except Exception as e:
        logger.error(f"Search GET error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/affiliate/products")
async def list_affiliate_products(
    req: Request,
    provider: str = Query(..., description="Provider: mercadolivre, shopee, aliexpress, lomadee"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=20, le=100),
    sort: str = Query(default="relevance", description="sort: relevance, price_asc, price_desc"),
    search: str = Query(default="", description="Busca específica opcional (ex: iphone x)"),
):
    """Lista produtos afiliados por provider com paginação e busca opcional."""
    from app.core.rate_limit import check_rate_limit, get_client_ip
    from app.services.search import search_all
    from app.schemas.schemas import ProviderEnum
    ip = get_client_ip(req)
    if not await check_rate_limit(ip, key="affiliate", max_calls=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit: max 60 req/min por IP.")
    
    try:
        # Para AliExpress sem busca específica, usar hot products
        if provider == "aliexpress" and (not search or len(search) < 2):
            from app.integrations.aliexpress import AliExpressClient
            from app.services.providers.aliexpress import AliExpressProvider
            
            client = AliExpressClient()
            provider_instance = AliExpressProvider()
            
            hot_products = await client.get_hot_products(limit=100)
            
            # Converter ProductResult para OfferSchema
            offers = [provider_instance._to_offer(p) for p in hot_products]
            
            # Ordenação
            if sort == "price_asc":
                offers = sorted(offers, key=lambda x: x.final_price or float('inf'))
            elif sort == "price_desc":
                offers = sorted(offers, key=lambda x: x.final_price or 0, reverse=True)
            
            # Simula paginação
            offset = (page - 1) * per_page
            paginated_offers = offers[offset:offset + per_page]
            return {
                "offers": paginated_offers,
                "total": len(offers),
                "page": page,
                "per_page": per_page,
                "total_pages": (len(offers) + per_page - 1) // per_page,
                "sort": sort,
            }
        
        # Sem busca específica, retornar vazio (não usar queries genéricas)
        if not search or len(search) < 2:
            return {
                "offers": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "total_pages": 0,
                "sort": sort,
            }
        
        # Busca com o que o usuário digitou
        query = search
        
        # Lomadee tem rate limit de 60 req/60s no shortener — limita a 20 produtos
        search_limit = 20 if provider == "lomadee" else 100
        
        # Busca mais produtos para permitir paginação (seguindo documentação oficial)
        result = await search_all(
            query=query,
            limit=search_limit,
            providers=[ProviderEnum(provider)],
        )
        
        # Filtrar ofertas pelo provider solicitado (garantia extra)
        offers = [offer for offer in result.offers if offer.provider == provider]
        
        # Ordenação
        if sort == "price_asc":
            offers = sorted(offers, key=lambda x: x.final_price or float('inf'))
        elif sort == "price_desc":
            offers = sorted(offers, key=lambda x: x.final_price or 0, reverse=True)
        # relevance usa a ordem padrão do ranking
        
        # Simula paginação calculando offset
        offset = (page - 1) * per_page
        paginated_offers = offers[offset:offset + per_page]
        return {
            "offers": paginated_offers,
            "total": len(offers),
            "page": page,
            "per_page": per_page,
            "total_pages": (len(offers) + per_page - 1) // per_page,
            "sort": sort,
        }
    except Exception as e:
        logger.error(f"Affiliate products error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list products: {str(e)}")


@router.get("/search/trending", response_model=TrendingSearchResponse)
async def trending_searches(limit: int = Query(default=20, ge=1, le=20)):
    try:
        items = await get_trending_searches(limit=limit)
        return TrendingSearchResponse(
            items=[TrendingSearchItem(**item) for item in items],
        )
    except Exception as e:
        logger.error(f"Trending search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trending search failed: {str(e)}")


# Curadoria de queries importada do módulo de dados (6700+ queries)
# Usado pelo sitemap para garantir páginas indexáveis mesmo com pouco tráfego
from app.data.curated_queries import CURATED_QUERIES


@router.get("/search/sitemap-queries")
async def sitemap_queries(limit: int = Query(default=500, ge=1, le=10000)):
    """Retorna queries para o sitemap — SÓ queries com ofertas reais.

    IMPORTANTE: Não incluir queries vazias (thin content prejudica SEO).
    As queries curadas foram testadas e todas retornam ≥3 ofertas.
    Trending queries não são incluídas porque a maioria retorna 0 ofertas
    (são acessórios filtrados pelo ranking engine).
    """
    result = []
    for q in CURATED_QUERIES:
        if len(result) >= limit:
            break
        result.append({
            "query": q,
            "score": 50,
            "source": "curated",
        })

    return {
        "count": len(result),
        "queries": result[:limit],
    }


@router.get("/debug/aliexpress")
async def debug_aliexpress(q: str = Query(default="fone bluetooth")):
    """Endpoint de diagnóstico — mostra resposta bruta da API AliExpress."""
    import hashlib, hmac, time, httpx, os
    from app.core.config import settings
    app_key    = settings.ALIEXPRESS_APP_KEY
    app_secret = settings.ALIEXPRESS_APP_SECRET
    tracking   = settings.ALIEXPRESS_TRACKING_ID
    if not app_key or not app_secret:
        return {"error": "not_configured", "app_key_set": bool(app_key)}
    ts = str(int(time.time() * 1000))
    params = {
        "app_key": app_key, "sign_method": "sha256", "timestamp": ts,
        "method": "aliexpress.affiliate.product.query",
        "keywords": q, "page_size": "5",
        "target_currency": "BRL", "target_language": "PT", "ship_to_country": "BR",
    }
    if tracking:
        params["tracking_id"] = tracking
    msg = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sig = hmac.new(app_secret.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()
    params["sign"] = sig
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post("https://api-sg.aliexpress.com/sync", data=params)
        d = r.json()
        resp = d.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {})
        products = resp.get("result", {}).get("products", {}).get("product", [])
        return {
            "http_status": r.status_code,
            "resp_code": resp.get("resp_code"),
            "resp_msg": resp.get("resp_msg"),
            "product_count": len(products),
            "titles": [p.get("product_title", "")[:60] for p in products[:3]],
            "app_key_prefix": app_key[:6] + "...",
        }
    except Exception as e:
        return {"error": str(e)}
