"""
Entry point of the recommendations module towards the rest of the application.

`main.py` only imports `create_recommendations_router()`.
"""
from fastapi import APIRouter

from app.recommendations.presentation.http.routers.discovery_router import router as discovery_router


def create_recommendations_router() -> APIRouter:
    router = APIRouter()
    router.include_router(discovery_router)
    return router
