"""SQLAlchemy ORM model for `ingredient_categories`: the display names of the ingredient category codes."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class IngredientCategoryModel(LocalizedNameMixin, Base):
    """`ingredients.default_category` holds the stable `code` ("flour"); this table names it per language.

    Not a foreign key on purpose: a code without a row here is still valid and is
    shown as written (categories used to be free text, see migration 0017).
    """

    __tablename__ = "ingredient_categories"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
