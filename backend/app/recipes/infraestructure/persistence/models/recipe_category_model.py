"""SQLAlchemy ORM model for the `recipe_categories` table (seeded catalog)."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class RecipeCategoryModel(LocalizedNameMixin, Base):
    __tablename__ = "recipe_categories"

    # names / name_language: see LocalizedNameMixin (unique per language, migration 0017).
