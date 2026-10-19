"""
SQLAlchemy ORM models for preparations: the session, and its own copy of
the recipe's steps (with per-step progress) and ingredient lines.

Ingredient, unit and source-step ids are stored as opaque values without
foreign keys: they belong to other modules and the copy must outlive any
change to them.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class PreparationSessionModel(Base):
    __tablename__ = "preparation_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')", name="ck_preparation_sessions_status"
        ),
        # At most one preparation in progress per user and recipe.
        Index(
            "uq_preparation_in_progress",
            "user_id",
            "recipe_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    recipe_title: Mapped[str] = mapped_column(String(200), nullable=False)
    cover_photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_step_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PreparationStepModel(Base):
    __tablename__ = "preparation_steps"
    __table_args__ = (UniqueConstraint("session_id", "step_number", name="uq_preparation_step_number"),)

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preparation_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    timer_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_step_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timer_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PreparationIngredientModel(Base):
    __tablename__ = "preparation_ingredients"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("preparation_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Snapshot of the ingredient's name in every language (+ the one it was written in).
    ingredient_names: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ingredient_name_language: Mapped[str | None] = mapped_column(String(2), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    unit_abbreviation: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
