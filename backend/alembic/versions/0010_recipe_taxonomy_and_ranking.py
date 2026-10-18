"""
recipe taxonomy (finer categories + tags) and ranking support

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-18

- Categories: "Tortas y pasteles" -> "Tortas", "Cupcakes y muffins" -> "Cupcakes",
  plus new "Muffins" and "Brownies y barras". Renamed in place, so ids (and
  the recipes pointing to them) are preserved.
- Tags: controlled catalog (`tags`) + many-to-many `recipe_tags`, seeded.
- `recipes.ingredient_count`: denormalized number of distinct ingredients,
  backfilled here, used as the denominator of the SQL compatibility ranking.
- `recipe_ingredients (ingredient_id, recipe_id)` index: lets the ranking
  find "recipes using any of these ingredients" from the index alone.
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_RENAMED_CATEGORIES = [("Tortas y pasteles", "Tortas"), ("Cupcakes y muffins", "Cupcakes")]
_NEW_CATEGORIES = ["Muffins", "Brownies y barras"]

_SEED_TAGS = [
    "Chocolate",
    "Frutal",
    "Frutos secos",
    "Sin gluten",
    "Sin lactosa",
    "Vegana",
    "Sin azúcar añadida",
    "Sin horno",
    "Rápida",
    "Navidad",
    "Cumpleaños",
    "Para regalar",
]


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    # ---------------------------------------------------------------- categories
    categories = sa.table("recipe_categories", sa.column("id"), sa.column("name"))
    for old_name, new_name in _RENAMED_CATEGORIES:
        op.execute(categories.update().where(categories.c.name == old_name).values(name=new_name))
    op.bulk_insert(
        sa.table("recipe_categories", sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("name", sa.String)),
        [{"id": uuid.uuid4(), "name": name} for name in _NEW_CATEGORIES],
    )

    # ---------------------------------------------------------------- tags
    tags_table = op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False, unique=True),
        *_timestamp_columns(),
    )
    op.create_table(
        "recipe_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipe_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id"), nullable=False),
        *_timestamp_columns(),
        sa.UniqueConstraint("recipe_id", "tag_id", name="uq_recipe_tag"),
    )
    op.create_index("ix_recipe_tags_recipe_id", "recipe_tags", ["recipe_id"])
    op.create_index("ix_recipe_tags_tag_id", "recipe_tags", ["tag_id"])
    op.bulk_insert(tags_table, [{"id": uuid.uuid4(), "name": name} for name in _SEED_TAGS])

    # ---------------------------------------------------------------- ranking support
    op.add_column("recipes", sa.Column("ingredient_count", sa.Integer, nullable=False, server_default="0"))
    op.execute(
        """
        UPDATE recipes r
        SET ingredient_count = sub.total
        FROM (
            SELECT recipe_id, COUNT(DISTINCT ingredient_id) AS total
            FROM recipe_ingredients
            GROUP BY recipe_id
        ) AS sub
        WHERE sub.recipe_id = r.id
        """
    )
    op.drop_index("ix_recipe_ingredients_ingredient_id", table_name="recipe_ingredients")
    op.create_index(
        "ix_recipe_ingredients_ingredient_recipe", "recipe_ingredients", ["ingredient_id", "recipe_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_recipe_ingredients_ingredient_recipe", table_name="recipe_ingredients")
    op.create_index("ix_recipe_ingredients_ingredient_id", "recipe_ingredients", ["ingredient_id"])
    op.drop_column("recipes", "ingredient_count")

    op.drop_index("ix_recipe_tags_tag_id", table_name="recipe_tags")
    op.drop_index("ix_recipe_tags_recipe_id", table_name="recipe_tags")
    op.drop_table("recipe_tags")
    op.drop_table("tags")

    # Recipes in the new categories go back to the closest old one before removing them.
    op.execute(
        """
        UPDATE recipes SET category_id = (SELECT id FROM recipe_categories WHERE name = 'Cupcakes')
        WHERE category_id = (SELECT id FROM recipe_categories WHERE name = 'Muffins')
        """
    )
    op.execute(
        """
        UPDATE recipes SET category_id = NULL
        WHERE category_id = (SELECT id FROM recipe_categories WHERE name = 'Brownies y barras')
        """
    )
    categories = sa.table("recipe_categories", sa.column("id"), sa.column("name"))
    op.execute(categories.delete().where(categories.c.name.in_(_NEW_CATEGORIES)))
    for old_name, new_name in _RENAMED_CATEGORIES:
        op.execute(categories.update().where(categories.c.name == new_name).values(name=old_name))
