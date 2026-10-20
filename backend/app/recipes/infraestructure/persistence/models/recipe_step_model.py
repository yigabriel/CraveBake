"""SQLAlchemy ORM model for the `recipe_steps` table."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RecipeStepModel(Base):
    __tablename__ = "recipe_steps"
    # Deferred so steps can be renumbered inside one transaction without
    # transiently colliding (e.g. swapping steps 1 and 2).
    __table_args__ = (
        UniqueConstraint(
            "recipe_id", "step_number", name="uq_recipe_step_number", deferrable=True, initially="DEFERRED"
        ),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    timer_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe_sections.id", ondelete="SET NULL"), nullable=True, index=True
    )
