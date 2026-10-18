"""SQLAlchemy ORM model for the `difficulties` table (seeded catalog)."""
from __future__ import annotations

from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class DifficultyModel(Base):
    __tablename__ = "difficulties"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    level_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
