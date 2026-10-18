"""
add category / tag filters to discovery_sessions

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-18

Ids of the recipes context are stored as opaque values (no foreign key):
the catalogs belong to another module, and a session only remembers which
filters it was started with.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("discovery_sessions", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "discovery_sessions",
        sa.Column("tag_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("discovery_sessions", "tag_ids")
    op.drop_column("discovery_sessions", "category_id")
