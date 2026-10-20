"""
Alembic environment.

Wires Alembic to the app's async engine and to the shared declarative
metadata (`Base`). Every bounded context's ORM models must be imported
here (even if unused directly) so `autogenerate` can see their tables.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.shared.config.settings import get_settings
from app.shared.database.base import Base

# Import every module's ORM models so Base.metadata knows about their tables.
import app.iam.infraestructure.persistence.models.user_model  # noqa: F401,E402
import app.ingredients.infrastructure.persistence.models.ingredient_model  # noqa: F401,E402
import app.ingredients.infrastructure.persistence.models.ingredient_unit_conversion_model  # noqa: F401,E402
import app.ingredients.infrastructure.persistence.models.unit_model  # noqa: F401,E402
import app.ingredients.infrastructure.persistence.models.user_ingredient_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_category_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.difficulty_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_section_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_step_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_ingredient_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_photo_model  # noqa: F401,E402
import app.portfolio.infraestructure.persistence.models.saved_recipe_model  # noqa: F401,E402
import app.equipment.infraestructure.persistence.models.equipment_model  # noqa: F401,E402
import app.equipment.infraestructure.persistence.models.user_equipment_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.recipe_equipment_model  # noqa: F401,E402
import app.recipes.infraestructure.persistence.models.tag_models  # noqa: F401,E402
import app.recommendations.infraestructure.persistence.models.discovery_models  # noqa: F401,E402
import app.preparation.infraestructure.persistence.models.preparation_models  # noqa: F401,E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())