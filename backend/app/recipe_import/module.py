"""
Entry point of the recipe-import module (a TikTok / Instagram Reel link -> a recipe draft).

`main.py` only imports `create_recipe_import_router()`.
"""
from fastapi import APIRouter

from app.recipe_import.presentation.http.routers.recipe_import_router import router as recipe_import_router


def create_recipe_import_router() -> APIRouter:
    router = APIRouter()
    router.include_router(recipe_import_router)
    return router
