"""
Entry point of the ingredients module towards the rest of the application.

Mounts five routers under one module: the ingredients catalog, categories,
the units reference catalog, the authenticated user's pantry, and the
measurement converter. `main.py` only imports `create_ingredients_router()`.
"""
from fastapi import APIRouter

from app.ingredients.presentation.http.routers.categories_router import router as categories_router
from app.ingredients.presentation.http.routers.converter_router import router as converter_router
from app.ingredients.presentation.http.routers.ingredients_router import (
    router as ingredients_router,
)
from app.ingredients.presentation.http.routers.pantry_router import router as pantry_router
from app.ingredients.presentation.http.routers.units_router import router as units_router


def create_ingredients_router() -> APIRouter:
    router = APIRouter()
    router.include_router(ingredients_router)
    router.include_router(categories_router)
    router.include_router(units_router)
    router.include_router(pantry_router)
    router.include_router(converter_router)
    return router
