"""fix egg white / yolk cup conversions (they held the weight of ONE egg, not of a cup)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-19

0003 seeded "1 cup of egg white = 35 g" and "1 cup of yolk = 20 g": those are
the weights of a single large white and yolk. A cup (236.6 ml) of either,
at ~1.03 g/ml, weighs ~240 g (King Arthur Baking's ingredient weight chart
and most baking tables agree within a few grams).
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_FIXED = {"Huevo, clara": ("35", "240"), "Huevo, yema": ("20", "240")}

_UPDATE = sa.text(
    """
    UPDATE ingredient_unit_conversions AS c
    SET grams_equivalent = CAST(:grams AS NUMERIC), updated_at = now()
    FROM ingredients AS i, units AS u
    WHERE c.ingredient_id = i.id AND c.unit_id = u.id
      AND i.name = :name AND u.abbreviation = 'cup' AND c.grams_equivalent = CAST(:previous AS NUMERIC)
    """
)


def upgrade() -> None:
    for name, (wrong, right) in _FIXED.items():
        # Only touches the seeded value, never a figure someone already corrected by hand.
        op.execute(_UPDATE.bindparams(name=name, grams=right, previous=wrong))


def downgrade() -> None:
    for name, (wrong, right) in _FIXED.items():
        op.execute(_UPDATE.bindparams(name=name, grams=wrong, previous=right))
