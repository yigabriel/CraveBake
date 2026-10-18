"""SQLAlchemy ORM model for the `ingredient_unit_conversions` table."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class IngredientUnitConversionModel(Base):
    __tablename__ = "ingredient_unit_conversions"
    __table_args__ = (UniqueConstraint("ingredient_id", "unit_id", name="uq_ingredient_unit"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    grams_equivalent: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
