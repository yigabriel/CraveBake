"""show the regional synonyms of butter in its Spanish name: "Mantequilla / Manteca"

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-21

"Manteca" is butter in Argentina and lard in Spain or Mexico; "mantequilla" is
butter in Peru and most of Latin America. The seeded ingredient was only called
"Manteca", so a Peruvian baker would not recognise it. Its Spanish name now lists
both words. `name_equals` understands the " / " convention, so typing either word
is recognised as this ingredient instead of creating a duplicate.

Only the exact seeded row is renamed (Spanish "Manteca" with English "Butter"): a
user's own ingredient that happens to be called "Manteca" is left alone.
"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

_OLD = "Manteca"
_NEW = "Mantequilla / Manteca"


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE ingredients SET names = jsonb_set(names, '{es}', to_jsonb(CAST(:new AS text))) "
            "WHERE names->>'es' = :old AND names->>'en' = 'Butter' "
            # Never create a clash: another row already using the new name keeps the old one.
            "AND NOT EXISTS (SELECT 1 FROM ingredients WHERE lower(names->>'es') = lower(:new))"
        ).bindparams(old=_OLD, new=_NEW)
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE ingredients SET names = jsonb_set(names, '{es}', to_jsonb(CAST(:old AS text))) "
            "WHERE names->>'es' = :new AND names->>'en' = 'Butter'"
        ).bindparams(old=_OLD, new=_NEW)
    )
