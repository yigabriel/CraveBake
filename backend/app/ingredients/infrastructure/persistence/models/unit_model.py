"""SQLAlchemy ORM model for the `units` table."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.localized_name import LocalizedNameMixin


class UnitModel(LocalizedNameMixin, Base):
    # names / name_language: see LocalizedNameMixin (migration 0017). `abbreviation` is the stable code.
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    abbreviation: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    unit_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    base_factor: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
    )

    unit_system: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )