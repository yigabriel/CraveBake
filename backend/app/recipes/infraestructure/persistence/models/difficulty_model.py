"""SQLAlchemy ORM model for the `difficulties` table (seeded catalog)."""
from __future__ import annotations

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class DifficultyModel(LocalizedNameMixin, Base):
    __tablename__ = "difficulties"

    # names / name_language: see LocalizedNameMixin (unique per language, migration 0017).
    level_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
