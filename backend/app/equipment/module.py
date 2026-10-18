"""
Entry point of the equipment module towards the rest of the application.

`main.py` only imports `create_equipment_router()`.
"""
from fastapi import APIRouter

from app.equipment.presentation.http.routers.equipment_router import router as equipment_router


def create_equipment_router() -> APIRouter:
    router = APIRouter()
    router.include_router(equipment_router)
    return router
