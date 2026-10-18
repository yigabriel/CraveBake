"""SQLAlchemy ORM model for the `user_equipment` table (the user's kitchen)."""
from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class UserEquipmentModel(Base):
    __tablename__ = "user_equipment"
    __table_args__ = (
        UniqueConstraint("user_id", "equipment_id", name="uq_user_equipment"),
        CheckConstraint("quantity >= 1", name="ck_user_equipment_quantity"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipment.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
