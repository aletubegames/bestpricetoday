from fastapi import APIRouter
from app.api.v1.endpoints import search, alerts, favorites, products, auth

api_router = APIRouter()
api_router.include_router(search.router, tags=["search"])
api_router.include_router(alerts.router, tags=["alerts"])
api_router.include_router(favorites.router, tags=["favorites"])
api_router.include_router(products.router, tags=["products"])
api_router.include_router(auth.router, tags=["auth"])
