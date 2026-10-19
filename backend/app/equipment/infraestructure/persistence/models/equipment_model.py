"""SQLAlchemy ORM model for the `equipment` table (shared catalog)."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class EquipmentModel(LocalizedNameMixin, Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(
            "equipment_type IN ('molde', 'utensilio', 'electrodomestico', 'otro')", name="ck_equipment_type"
        ),
    )

    # names / name_language: see LocalizedNameMixin (unique per language, migration 0017).
    equipment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
