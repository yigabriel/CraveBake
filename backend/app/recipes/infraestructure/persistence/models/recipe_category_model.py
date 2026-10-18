"""SQLAlchemy ORM model for the `recipe_categories` table (seeded catalog)."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RecipeCategoryModel(Base):
    __tablename__ = "recipe_categories"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
