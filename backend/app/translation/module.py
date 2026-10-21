"""
Entry point of the translation module (suggested translations of catalog names).

`main.py` only imports `create_translation_router()`.
"""
from fastapi import APIRouter

from app.translation.presentation.http.routers.translation_router import router as translation_router


def create_translation_router() -> APIRouter:
    router = APIRouter()
    router.include_router(translation_router)
    return router
