"""
Composition root for the equipment module.

Wires domain interfaces to their SQLAlchemy implementations, builds each use
case, and provides the module's public API (`EquipmentQueryService`) to
other bounded contexts.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.equipment.application.use_cases.equipment_catalog_use_cases import (
    CreateEquipmentUseCase,
    GetEquipmentUseCase,
    SearchEquipmentUseCase,
)
from app.equipment.application.use_cases.user_equipment_use_cases import (
    ListUserEquipmentUseCase,
    RemoveUserEquipmentUseCase,
    UpsertUserEquipmentUseCase,
)
from app.equipment.domain.repositories.equipment_repositories import (
    EquipmentRepository,
    UserEquipmentRepository,
)
from app.equipment.infraestructure.persistence.repositories.sqlalchemy_equipment_repositories import (
    SqlAlchemyEquipmentRepository,
    SqlAlchemyUserEquipmentRepository,
)
from app.shared.database.session import get_db_session

# --- Repositories -------------------------------------------------------------------


def get_equipment_repository(session: AsyncSession = Depends(get_db_session)) -> EquipmentRepository:
    return SqlAlchemyEquipmentRepository(session)


def get_user_equipment_repository(session: AsyncSession = Depends(get_db_session)) -> UserEquipmentRepository:
    return SqlAlchemyUserEquipmentRepository(session)


# --- Use cases ------------------------------------------------------------------------


def get_search_equipment_use_case(
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
) -> SearchEquipmentUseCase:
    return SearchEquipmentUseCase(equipment_repository)


def get_get_equipment_use_case(
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
) -> GetEquipmentUseCase:
    return GetEquipmentUseCase(equipment_repository)


def get_create_equipment_use_case(
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
) -> CreateEquipmentUseCase:
    return CreateEquipmentUseCase(equipment_repository)


def get_list_user_equipment_use_case(
    user_equipment_repository: UserEquipmentRepository = Depends(get_user_equipment_repository),
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
) -> ListUserEquipmentUseCase:
    return ListUserEquipmentUseCase(user_equipment_repository, equipment_repository)


def get_upsert_user_equipment_use_case(
    user_equipment_repository: UserEquipmentRepository = Depends(get_user_equipment_repository),
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
) -> UpsertUserEquipmentUseCase:
    return UpsertUserEquipmentUseCase(user_equipment_repository, equipment_repository)


def get_remove_user_equipment_use_case(
    user_equipment_repository: UserEquipmentRepository = Depends(get_user_equipment_repository),
) -> RemoveUserEquipmentUseCase:
    return RemoveUserEquipmentUseCase(user_equipment_repository)


# --- Public API for other bounded contexts ---------------------------------------


def get_equipment_query_service(
    equipment_repository: EquipmentRepository = Depends(get_equipment_repository),
    user_equipment_repository: UserEquipmentRepository = Depends(get_user_equipment_repository),
) -> EquipmentQueryService:
    """Provider other modules' composition roots use to reach the equipment Open Host Service."""
    return EquipmentQueryService(equipment_repository, user_equipment_repository)
