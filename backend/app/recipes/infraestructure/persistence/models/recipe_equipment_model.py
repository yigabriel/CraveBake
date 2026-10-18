"""SQLAlchemy ORM model for the `recipe_equipment` table (equipment a recipe needs)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RecipeEquipmentModel(Base):
    __tablename__ = "recipe_equipment"
    __table_args__ = (UniqueConstraint("recipe_id", "equipment_id", name="uq_recipe_equipment"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
