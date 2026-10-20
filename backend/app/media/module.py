"""
Entry point of the media module (photo uploads) towards the rest of the application.

`main.py` only imports `create_media_router()`.
"""
from fastapi import APIRouter

from app.media.presentation.http.routers.media_router import router as media_router


def create_media_router() -> APIRouter:
    router = APIRouter()
    router.include_router(media_router)
    return router
