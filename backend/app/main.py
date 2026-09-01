"""
Application entry point.

Wires together shared infrastructure (exception handlers) and mounts each
bounded context's router. Bounded contexts are added here as they get
implemented — currently only `iam`.
"""
from fastapi import FastAPI

from app.iam.module import create_iam_router
from app.shared.config.settings import get_settings
from app.shared.exceptions.exception_handlers import register_exception_handlers

from app.shared.database.session import engine

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Pastry API — discover, save, personalize and cook pastry recipes.",
    debug=settings.debug,
)

register_exception_handlers(app)

app.include_router(create_iam_router())


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database", tags=["Health"])
async def database_health_check() -> dict[str, str]:
    from sqlalchemy import text

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return {"database": "connected"}
