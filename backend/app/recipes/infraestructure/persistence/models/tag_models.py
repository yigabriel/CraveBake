"""SQLAlchemy ORM models for the `tags` catalog and the `recipe_tags` link table."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class TagModel(LocalizedNameMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint(
            "tag_group IN ('flavor', 'diet', 'technique', 'time', 'celebrations')", name="ck_tags_group"
        ),
    )

    # names / name_language: see LocalizedNameMixin (unique per language, migration 0017).
    # `group` is a reserved word in SQL, hence the prefix.
    tag_group: Mapped[str] = mapped_column(String(20), nullable=False)


class RecipeTagModel(Base):
    __tablename__ = "recipe_tags"
    __table_args__ = (UniqueConstraint("recipe_id", "tag_id", name="uq_recipe_tag"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, index=True
    )
