"""
Entry point of the recipes module towards the rest of the application.

Mounts the recipes router (CRUD, search, personalization), the photos
router and the catalogs router (categories, difficulties). `main.py` only
imports `create_recipes_router()`.
"""
from fastapi import APIRouter

from app.recipes.presentation.http.routers.recipe_catalogs_router import router as recipe_catalogs_router
from app.recipes.presentation.http.routers.recipe_photos_router import router as recipe_photos_router
from app.recipes.presentation.http.routers.recipes_router import router as recipes_router


def create_recipes_router() -> APIRouter:
    router = APIRouter()
    router.include_router(recipes_router)
    router.include_router(recipe_photos_router)
    router.include_router(recipe_catalogs_router)
    return router
