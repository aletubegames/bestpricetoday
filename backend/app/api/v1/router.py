from fastapi import APIRouter
from app.api.v1.endpoints import search, alerts

api_router = APIRouter()
api_router.include_router(search.router, tags=["search"])
api_router.include_router(alerts.router, tags=["alerts"])
