"""
create ingredients, units, ingredient_unit_conversions, user_ingredients tables
+ seed default units

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-31
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


# Seeded once here so the /converter and /units endpoints have something to
# work with immediately after migrating, without a separate manual step.
_SEED_UNITS = [
    # (name, abbreviation, unit_type, base_factor)
    ("gramo", "g", "weight", "1"),
    ("kilogramo", "kg", "weight", "1000"),
    ("onza", "oz", "weight", "28.3495"),
    ("mililitro", "ml", "volume", "1"),
    ("litro", "l", "volume", "1000"),
    ("taza", "cup", "volume", "236.588"),
    ("cucharada", "tbsp", "volume", "14.7868"),
    ("cucharadita", "tsp", "volume", "4.92892"),
    ("unidad", "u", "count", "1"),
]


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # INGREDIENTS
    # -------------------------------------------------------------------------
    op.create_table(
        "ingredients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "description",
            sa.String(1024),
            nullable=True,
        ),
        sa.Column(
            "default_category",
            sa.String(100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_ingredients_name",
        "ingredients",
        ["name"],
    )

    # -------------------------------------------------------------------------
    # UNITS
    # -------------------------------------------------------------------------
    units_table = op.create_table(
        "units",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "name",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "abbreviation",
            sa.String(10),
            nullable=False,
        ),
        sa.Column(
            "unit_type",
            sa.String(10),
            nullable=False,
        ),
        sa.Column(
            "base_factor",
            sa.Numeric(12, 6),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # -------------------------------------------------------------------------
    # INGREDIENT UNIT CONVERSIONS
    # -------------------------------------------------------------------------
    op.create_table(
        "ingredient_unit_conversions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "ingredient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "ingredients.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id"),
            nullable=False,
        ),
        sa.Column(
            "grams_equivalent",
            sa.Numeric(12, 4),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "ingredient_id",
            "unit_id",
            name="uq_ingredient_unit",
        ),
    )

    # -------------------------------------------------------------------------
    # USER INGREDIENTS
    # -------------------------------------------------------------------------
    op.create_table(
        "user_ingredients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "ingredient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingredients.id"),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(12, 4),
            nullable=True,
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("units.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "ingredient_id",
            name="uq_user_ingredient",
        ),
    )

    # -------------------------------------------------------------------------
    # SEED DEFAULT UNITS
    # -------------------------------------------------------------------------
    op.bulk_insert(
        units_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "abbreviation": abbreviation,
                "unit_type": unit_type,
                "base_factor": base_factor,
            }
            for name, abbreviation, unit_type, base_factor in _SEED_UNITS
        ],
    )


def downgrade() -> None:
    op.drop_table("user_ingredients")

    op.drop_table("ingredient_unit_conversions")

    op.drop_table("units")

    op.drop_index(
        "ix_ingredients_name",
        table_name="ingredients",
    )

    op.drop_table("ingredients")