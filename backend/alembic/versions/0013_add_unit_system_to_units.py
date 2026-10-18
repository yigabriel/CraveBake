"""
add unit_system to units (metric | us | neutral)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-18

Lets quantities be shown in the user's preferred unit system: the converter
needs to know which tradition each unit belongs to.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_SYSTEM_BY_ABBREVIATION = {
    "g": "metric",
    "kg": "metric",
    "ml": "metric",
    "l": "metric",
    "cup": "us",
    "tbsp": "us",
    "tsp": "us",
    "oz": "us",
    "u": "neutral",
}


def upgrade() -> None:
    op.add_column("units", sa.Column("unit_system", sa.String(10), nullable=True))
    units = sa.table("units", sa.column("abbreviation"), sa.column("unit_system"))
    for abbreviation, system in _SYSTEM_BY_ABBREVIATION.items():
        op.execute(units.update().where(units.c.abbreviation == abbreviation).values(unit_system=system))
    op.execute(units.update().where(units.c.unit_system.is_(None)).values(unit_system="neutral"))
    op.alter_column("units", "unit_system", nullable=False)


def downgrade() -> None:
    op.drop_column("units", "unit_system")
