"""SQLAlchemy ORM model for the `recipe_sections` table."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RecipeSectionModel(Base):
    __tablename__ = "recipe_sections"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


# A recipe has one "Masa choux", however it was typed (also serves lookups by recipe).
Index("uq_recipe_sections_name", RecipeSectionModel.recipe_id, func.lower(RecipeSectionModel.name), unique=True)
