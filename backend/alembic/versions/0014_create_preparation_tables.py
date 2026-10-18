"""
create preparation tables (guided cooking mode + history)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-18

A preparation keeps its own copy of the recipe (steps and ingredient lines)
taken when cooking starts. Ingredient, unit and source-step ids are opaque
(no FK): they belong to other modules and the copy must outlive changes there.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "preparation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("recipe_title", sa.String(200), nullable=False),
        sa.Column("cover_photo_url", sa.String(1024), nullable=True),
        sa.Column("servings", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_step_number", sa.SmallInteger, nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')", name="ck_preparation_sessions_status"
        ),
    )
    op.create_index("ix_preparation_sessions_user_id", "preparation_sessions", ["user_id"])
    op.create_index(
        "uq_preparation_in_progress",
        "preparation_sessions",
        ["user_id", "recipe_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )

    op.create_table(
        "preparation_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("preparation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.SmallInteger, nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("instructions", sa.Text, nullable=False),
        sa.Column("timer_seconds", sa.Integer, nullable=True),
        sa.Column("photo_url", sa.String(1024), nullable=True),
        sa.Column("source_step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timer_started_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.UniqueConstraint("session_id", "step_number", name="uq_preparation_step_number"),
    )
    op.create_index("ix_preparation_steps_session_id", "preparation_steps", ["session_id"])

    op.create_table(
        "preparation_ingredients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("preparation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ingredient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_name", sa.String(255), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_abbreviation", sa.String(10), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("position", sa.SmallInteger, nullable=False, server_default="0"),
        *_timestamp_columns(),
    )
    op.create_index("ix_preparation_ingredients_session_id", "preparation_ingredients", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_preparation_ingredients_session_id", table_name="preparation_ingredients")
    op.drop_table("preparation_ingredients")
    op.drop_index("ix_preparation_steps_session_id", table_name="preparation_steps")
    op.drop_table("preparation_steps")
    op.drop_index("uq_preparation_in_progress", table_name="preparation_sessions")
    op.drop_index("ix_preparation_sessions_user_id", table_name="preparation_sessions")
    op.drop_table("preparation_sessions")
