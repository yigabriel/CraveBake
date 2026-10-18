"""SQLAlchemy ORM model for the `recipe_photos` table (cover carousel + one photo per step)."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RecipePhotoModel(Base):
    __tablename__ = "recipe_photos"
    # The limits live in the `Recipe` aggregate; these constraints are an extra line of defense.
    __table_args__ = (
        CheckConstraint("photo_type IN ('cover', 'step')", name="ck_recipe_photos_type"),
        CheckConstraint(
            "(photo_type = 'step' AND step_id IS NOT NULL) OR (photo_type = 'cover' AND step_id IS NULL)",
            name="ck_recipe_photos_step_consistency",
        ),
        UniqueConstraint("step_id", name="uq_recipe_photos_step", deferrable=True, initially="DEFERRED"),
        Index("ix_recipe_photos_recipe_id", "recipe_id", "photo_type"),
    )

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False
    )
    photo_type: Mapped[str] = mapped_column(String(10), nullable=False)
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipe_steps.id", ondelete="CASCADE"), nullable=True
    )
    photo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
