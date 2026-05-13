from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.schemas.schemas import SearchRequest, SearchResponse
from app.services.search import search_all
from app.core.logging import logger
import time

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
