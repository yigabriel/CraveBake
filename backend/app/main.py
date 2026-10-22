"""
Application entry point.

Wires together shared infrastructure (exception handlers) and mounts each
bounded context's router under the `/v1` API version. Health checks stay
unversioned, since they are for infrastructure, not API clients.
"""
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

#Routers
from app.iam.module import create_iam_router
from app.ingredients.module import create_ingredients_router
from app.recipes.module import create_recipes_router
from app.portfolio.module import create_portfolio_router
from app.equipment.module import create_equipment_router
from app.recommendations.module import create_recommendations_router
from app.preparation.module import create_preparation_router
from app.media.module import create_media_router
from app.recipe_import.module import create_recipe_import_router
from app.translation.module import create_translation_router

from app.shared.config.settings import get_settings
from app.shared.exceptions.exception_handlers import register_exception_handlers

from app.shared.database.session import engine

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="CraveBake API - discover, save, personalize and cook pastry recipes.",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(create_iam_router())
api_v1.include_router(create_ingredients_router())
api_v1.include_router(create_recipes_router())
api_v1.include_router(create_portfolio_router())
api_v1.include_router(create_equipment_router())
api_v1.include_router(create_recommendations_router())
api_v1.include_router(create_preparation_router())
api_v1.include_router(create_media_router())
api_v1.include_router(create_translation_router())
api_v1.include_router(create_recipe_import_router())
app.include_router(api_v1)



@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database", tags=["Health"])
async def database_health_check() -> dict[str, str]:
    from sqlalchemy import text

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return {"database": "connected"}
