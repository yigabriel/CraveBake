"""
add created_at / updated_at to ingredient_unit_conversions

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13

Every ORM model inherits `created_at` and `updated_at` from the shared
`Base`, but 0002 created this table without them, so any ORM query on
`IngredientUnitConversionModel` (e.g. the /converter volume<->weight
lookup) selected columns that did not exist.
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column_name in ("created_at", "updated_at"):
        op.add_column(
            "ingredient_unit_conversions",
            sa.Column(column_name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_column("ingredient_unit_conversions", "updated_at")
    op.drop_column("ingredient_unit_conversions", "created_at")
