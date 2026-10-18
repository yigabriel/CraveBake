"""
Entry point of the preparation module towards the rest of the application.

`main.py` only imports `create_preparation_router()`.
"""
from fastapi import APIRouter

from app.preparation.presentation.http.routers.preparations_router import router as preparations_router


def create_preparation_router() -> APIRouter:
    router = APIRouter()
    router.include_router(preparations_router)
    return router
