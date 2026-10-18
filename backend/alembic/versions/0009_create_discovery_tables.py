"""
create discovery_sessions and discovery_swipes tables (recommendations)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-18

Replaces the data model's optional `discovery_interactions`: the selected
ingredients now live once per session (`discovery_sessions.ingredient_ids`)
instead of being repeated on every interaction, and each swipe records its
action and compatibility score.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "discovery_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ingredient_source", sa.String(20), nullable=False),
        sa.Column("ingredient_ids", postgresql.JSONB, nullable=False),
        sa.Column("min_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        *_timestamp_columns(),
        sa.CheckConstraint("ingredient_source IN ('selection', 'pantry')", name="ck_discovery_sessions_source"),
    )
    op.create_index("ix_discovery_sessions_user_id", "discovery_sessions", ["user_id"])

    op.create_table(
        "discovery_swipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discovery_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("compatibility_score", sa.Numeric(5, 4), nullable=False),
        *_timestamp_columns(),
        sa.UniqueConstraint("session_id", "recipe_id", name="uq_discovery_swipe_recipe"),
        sa.CheckConstraint("action IN ('discarded', 'saved', 'selected')", name="ck_discovery_swipes_action"),
    )
    op.create_index("ix_discovery_swipes_session_id", "discovery_swipes", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_discovery_swipes_session_id", table_name="discovery_swipes")
    op.drop_table("discovery_swipes")
    op.drop_index("ix_discovery_sessions_user_id", table_name="discovery_sessions")
    op.drop_table("discovery_sessions")
