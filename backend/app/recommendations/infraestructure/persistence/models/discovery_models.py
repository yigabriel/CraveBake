"""SQLAlchemy ORM models for `discovery_sessions` and `discovery_swipes`."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class DiscoverySessionModel(Base):
    __tablename__ = "discovery_sessions"
    __table_args__ = (
        CheckConstraint("ingredient_source IN ('selection', 'pantry')", name="ck_discovery_sessions_source"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_source: Mapped[str] = mapped_column(String(20), nullable=False)
    # Snapshot of the ingredient ids the session cooks with (selection or pantry at start time).
    ingredient_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    min_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    # Optional filters; opaque ids of the recipes context (no FK: catalogs are another module's data).
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tag_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class DiscoverySwipeModel(Base):
    __tablename__ = "discovery_swipes"
    __table_args__ = (
        UniqueConstraint("session_id", "recipe_id", name="uq_discovery_swipe_recipe"),
        CheckConstraint("action IN ('discarded', 'saved', 'selected')", name="ck_discovery_swipes_action"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    compatibility_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
