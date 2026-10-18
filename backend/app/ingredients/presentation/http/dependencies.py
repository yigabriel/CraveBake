"""
Composition root for the ingredients module.

Wires domain interfaces to their SQLAlchemy implementations and builds each
use case. Auth-protected endpoints reuse IAM's `get_current_user` — this
module depends on that one function from IAM's Presentation layer (the
public, stable seam between bounded contexts), never on IAM's Domain.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.iam.presentation.http.dependencies import get_current_user
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.application.use_cases.convert_measurement_use_case import (
    ConvertMeasurementUseCase,
)
from app.ingredients.application.use_cases.create_ingredient_use_case import CreateIngredientUseCase
from app.ingredients.application.use_cases.get_ingredient_use_case import GetIngredientUseCase
from app.ingredients.application.use_cases.list_categories_use_case import ListCategoriesUseCase
from app.ingredients.application.use_cases.list_units_use_case import ListUnitsUseCase
from app.ingredients.application.use_cases.list_user_ingredients_use_case import (
    ListUserIngredientsUseCase,
)
from app.ingredients.application.use_cases.remove_user_ingredient_use_case import (
    RemoveUserIngredientUseCase,
)
from app.ingredients.application.use_cases.search_ingredients_use_case import (
    SearchIngredientsUseCase,
)
from app.ingredients.application.use_cases.upsert_user_ingredient_use_case import (
    UpsertUserIngredientUseCase,
)
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.repositories.ingredient_unit_conversion_repository import (
    IngredientUnitConversionRepository,
)
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.services.measurement_converter import MeasurementConverter
from app.ingredients.domain.services.unit_system_converter import UnitSystemConverter
from app.ingredients.infrastructure.persistence.repositories.sqlalchemy_ingredient_repository import (
    SqlAlchemyIngredientRepository,
)
from app.ingredients.infrastructure.persistence.repositories.sqlalchemy_ingredient_unit_conversion_repository import (  # noqa: E501
    SqlAlchemyIngredientUnitConversionRepository,
)
from app.ingredients.infrastructure.persistence.repositories.sqlalchemy_unit_repository import (
    SqlAlchemyUnitRepository,
)
from app.ingredients.infrastructure.persistence.repositories.sqlalchemy_user_ingredient_repository import (  # noqa: E501
    SqlAlchemyUserIngredientRepository,
)
from app.shared.database.session import get_db_session

# --- Repositories -----------------------------------------------------------


def get_ingredient_repository(session: AsyncSession = Depends(get_db_session)) -> IngredientRepository:
    return SqlAlchemyIngredientRepository(session)


def get_unit_repository(session: AsyncSession = Depends(get_db_session)) -> UnitRepository:
    return SqlAlchemyUnitRepository(session)


def get_user_ingredient_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserIngredientRepository:
    return SqlAlchemyUserIngredientRepository(session)


def get_ingredient_unit_conversion_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IngredientUnitConversionRepository:
    return SqlAlchemyIngredientUnitConversionRepository(session)


def get_measurement_converter() -> MeasurementConverter:
    return MeasurementConverter()


# --- Use cases ----------------------------------------------------------------


def get_create_ingredient_use_case(
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
) -> CreateIngredientUseCase:
    return CreateIngredientUseCase(ingredient_repository)


def get_search_ingredients_use_case(
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
) -> SearchIngredientsUseCase:
    return SearchIngredientsUseCase(ingredient_repository)


def get_get_ingredient_use_case(
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
) -> GetIngredientUseCase:
    return GetIngredientUseCase(ingredient_repository)


def get_list_units_use_case(
    unit_repository: UnitRepository = Depends(get_unit_repository),
) -> ListUnitsUseCase:
    return ListUnitsUseCase(unit_repository)


def get_list_categories_use_case(
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
) -> ListCategoriesUseCase:
    return ListCategoriesUseCase(ingredient_repository)


def get_upsert_user_ingredient_use_case(
    user_ingredient_repository: UserIngredientRepository = Depends(get_user_ingredient_repository),
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
    unit_repository: UnitRepository = Depends(get_unit_repository),
) -> UpsertUserIngredientUseCase:
    return UpsertUserIngredientUseCase(user_ingredient_repository, ingredient_repository, unit_repository)


def get_remove_user_ingredient_use_case(
    user_ingredient_repository: UserIngredientRepository = Depends(get_user_ingredient_repository),
) -> RemoveUserIngredientUseCase:
    return RemoveUserIngredientUseCase(user_ingredient_repository)


def get_list_user_ingredients_use_case(
    user_ingredient_repository: UserIngredientRepository = Depends(get_user_ingredient_repository),
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
    unit_repository: UnitRepository = Depends(get_unit_repository),
) -> ListUserIngredientsUseCase:
    return ListUserIngredientsUseCase(user_ingredient_repository, ingredient_repository, unit_repository)


def get_convert_measurement_use_case(
    unit_repository: UnitRepository = Depends(get_unit_repository),
    ingredient_unit_conversion_repository: IngredientUnitConversionRepository = Depends(
        get_ingredient_unit_conversion_repository
    ),
    measurement_converter: MeasurementConverter = Depends(get_measurement_converter),
) -> ConvertMeasurementUseCase:
    return ConvertMeasurementUseCase(
        unit_repository, ingredient_unit_conversion_repository, measurement_converter
    )


# --- Public API for other bounded contexts ---------------------------------------


def get_ingredient_query_service(
    ingredient_repository: IngredientRepository = Depends(get_ingredient_repository),
    unit_repository: UnitRepository = Depends(get_unit_repository),
    user_ingredient_repository: UserIngredientRepository = Depends(get_user_ingredient_repository),
    conversion_repository: IngredientUnitConversionRepository = Depends(get_ingredient_unit_conversion_repository),
) -> IngredientQueryService:
    """Provider other modules' composition roots use to reach the ingredients Open Host Service."""
    return IngredientQueryService(
        ingredient_repository,
        unit_repository,
        user_ingredient_repository,
        conversion_repository,
        UnitSystemConverter(),
    )


__all__ = ["get_current_user"]  # re-exported for router modules that only need auth, not IAM internals
