"""SQLAlchemy ORM model for the `ingredients` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin
from app.ingredients.infrastructure.persistence.models.ingredient_category_model import IngredientCategoryModel


class IngredientModel(LocalizedNameMixin, Base):
    # names / name_language: see LocalizedNameMixin (unique per language, migration 0016).
    __tablename__ = "ingredients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    default_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Display name of the category code; joined so loading an ingredient is still one query.
    category: Mapped[IngredientCategoryModel | None] = relationship(
        IngredientCategoryModel,
        primaryjoin="foreign(IngredientModel.default_category) == IngredientCategoryModel.code",
        viewonly=True,
        lazy="joined",
    )
