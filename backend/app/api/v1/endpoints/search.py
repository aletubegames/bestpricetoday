from fastapi import APIRouter, HTTPException, Query
from app.schemas.schemas import SearchRequest, SearchResponse, TrendingSearchResponse, TrendingSearchItem
from app.services.search import get_trending_searches, search_all
from app.core.logging import logger

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
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
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
):
    try:
        return await search_all(query=q, limit=limit)
    except Exception as e:
        logger.error(f"Search GET error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


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
