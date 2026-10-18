"""
Entry point of the portfolio module towards the rest of the application.

`main.py` only imports `create_portfolio_router()`.
"""
from fastapi import APIRouter

from app.portfolio.presentation.http.routers.portfolio_router import router as portfolio_router


def create_portfolio_router() -> APIRouter:
    router = APIRouter()
    router.include_router(portfolio_router)
    return router
