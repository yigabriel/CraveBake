"""
create recipe_equipment table (equipment each recipe needs)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-18
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipe_equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("equipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("equipment.id"), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("recipe_id", "equipment_id", name="uq_recipe_equipment"),
    )
    op.create_index("ix_recipe_equipment_recipe_id", "recipe_equipment", ["recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_equipment_recipe_id", table_name="recipe_equipment")
    op.drop_table("recipe_equipment")
