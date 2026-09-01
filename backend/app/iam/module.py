"""
Entry point of the IAM module towards the rest of the application.

`main.py` does not need to know IAM has two internal routers (auth, users)
— it only imports `create_iam_router()` and mounts it. When the remaining
bounded contexts (recipes, ingredients, ...) are implemented, each will
expose its own `create_<module>_router()` following this same pattern.
"""
from fastapi import APIRouter

from app.iam.presentation.http.routers.auth_router import router as auth_router
from app.iam.presentation.http.routers.users_router import router as users_router


def create_iam_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(users_router)
    return router
