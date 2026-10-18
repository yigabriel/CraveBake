"""SQLAlchemy ORM model for the `user_saved_recipes` table (favorites).

The inherited `created_at` is the moment the recipe was saved (`saved_at`).
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class SavedRecipeModel(Base):
    __tablename__ = "user_saved_recipes"
    __table_args__ = (UniqueConstraint("user_id", "recipe_id", name="uq_user_saved_recipe"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # No cascade: recipes are only ever soft-deleted.
    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False, index=True
    )
