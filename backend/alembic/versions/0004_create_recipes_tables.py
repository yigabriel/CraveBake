"""
create recipes tables (recipes, steps, ingredients, photos) and catalogs
+ seed recipe categories and difficulties

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13

Business rules (max 3 cover photos, one photo per step, personalizations
always private, ...) live in the `Recipe` aggregate. The CHECK/UNIQUE
constraints here are an extra line of defense, not the primary mechanism.
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_SEED_CATEGORIES = [
    "Tortas y pasteles",
    "Galletas",
    "Panes y masas",
    "Tartas y pies",
    "Postres fríos",
    "Cupcakes y muffins",
]

# (name, level_order)
_SEED_DIFFICULTIES = [
    ("Fácil", 1),
    ("Intermedio", 2),
    ("Difícil", 3),
]


def _id_column() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _uuid_fk(name: str, target: str, nullable: bool = False, ondelete: str | None = None) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
    )


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # CATALOGS
    # -------------------------------------------------------------------------
    categories_table = op.create_table(
        "recipe_categories",
        _id_column(),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        *_timestamp_columns(),
    )

    difficulties_table = op.create_table(
        "difficulties",
        _id_column(),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("level_order", sa.SmallInteger, nullable=False),
        *_timestamp_columns(),
    )

    # -------------------------------------------------------------------------
    # RECIPES
    # -------------------------------------------------------------------------
    op.create_table(
        "recipes",
        _id_column(),
        _uuid_fk("created_by_user_id", "users.id", ondelete="CASCADE"),
        _uuid_fk("source_recipe_id", "recipes.id", nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("video_url", sa.String(1024), nullable=True),
        _uuid_fk("category_id", "recipe_categories.id", nullable=True),
        _uuid_fk("difficulty_id", "difficulties.id", nullable=True),
        sa.Column("prep_time_minutes", sa.Integer, nullable=True),
        sa.Column("servings", sa.Integer, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.CheckConstraint(
            "source_recipe_id IS NULL OR is_public = false", name="ck_recipes_personalization_private"
        ),
    )
    op.create_index("ix_recipes_created_by_user_id", "recipes", ["created_by_user_id"])
    op.create_index("ix_recipes_source_recipe_id", "recipes", ["source_recipe_id"])
    op.create_index("ix_recipes_category_id", "recipes", ["category_id"])
    op.create_index("ix_recipes_difficulty_id", "recipes", ["difficulty_id"])
    op.create_index(
        "ix_recipes_public",
        "recipes",
        ["is_public"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # -------------------------------------------------------------------------
    # STEPS
    # -------------------------------------------------------------------------
    op.create_table(
        "recipe_steps",
        _id_column(),
        _uuid_fk("recipe_id", "recipes.id", ondelete="CASCADE"),
        sa.Column("step_number", sa.SmallInteger, nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("instructions", sa.Text, nullable=False),
        sa.Column("timer_seconds", sa.Integer, nullable=True),
        *_timestamp_columns(),
        sa.UniqueConstraint(
            "recipe_id",
            "step_number",
            name="uq_recipe_step_number",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_index("ix_recipe_steps_recipe_id", "recipe_steps", ["recipe_id"])

    # -------------------------------------------------------------------------
    # INGREDIENT LINES
    # -------------------------------------------------------------------------
    op.create_table(
        "recipe_ingredients",
        _id_column(),
        _uuid_fk("recipe_id", "recipes.id", ondelete="CASCADE"),
        _uuid_fk("ingredient_id", "ingredients.id"),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        _uuid_fk("unit_id", "units.id"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("position", sa.SmallInteger, nullable=False, server_default="0"),
        *_timestamp_columns(),
        sa.CheckConstraint("quantity > 0", name="ck_recipe_ingredients_quantity_positive"),
    )
    op.create_index("ix_recipe_ingredients_recipe_id", "recipe_ingredients", ["recipe_id"])
    op.create_index("ix_recipe_ingredients_ingredient_id", "recipe_ingredients", ["ingredient_id"])

    # -------------------------------------------------------------------------
    # PHOTOS
    # -------------------------------------------------------------------------
    op.create_table(
        "recipe_photos",
        _id_column(),
        _uuid_fk("recipe_id", "recipes.id", ondelete="CASCADE"),
        sa.Column("photo_type", sa.String(10), nullable=False),
        _uuid_fk("step_id", "recipe_steps.id", nullable=True, ondelete="CASCADE"),
        sa.Column("photo_url", sa.String(1024), nullable=False),
        sa.Column("position", sa.SmallInteger, nullable=False, server_default="0"),
        *_timestamp_columns(),
        sa.CheckConstraint("photo_type IN ('cover', 'step')", name="ck_recipe_photos_type"),
        sa.CheckConstraint(
            "(photo_type = 'step' AND step_id IS NOT NULL) OR (photo_type = 'cover' AND step_id IS NULL)",
            name="ck_recipe_photos_step_consistency",
        ),
        # NULL step_ids (cover photos) never collide, so this only limits step photos.
        sa.UniqueConstraint("step_id", name="uq_recipe_photos_step", deferrable=True, initially="DEFERRED"),
    )
    op.create_index("ix_recipe_photos_recipe_id", "recipe_photos", ["recipe_id", "photo_type"])

    # -------------------------------------------------------------------------
    # SEEDS
    # -------------------------------------------------------------------------
    op.bulk_insert(categories_table, [{"id": uuid.uuid4(), "name": name} for name in _SEED_CATEGORIES])
    op.bulk_insert(
        difficulties_table,
        [{"id": uuid.uuid4(), "name": name, "level_order": order} for name, order in _SEED_DIFFICULTIES],
    )


def downgrade() -> None:
    op.drop_index("ix_recipe_photos_recipe_id", table_name="recipe_photos")
    op.drop_table("recipe_photos")

    op.drop_index("ix_recipe_ingredients_ingredient_id", table_name="recipe_ingredients")
    op.drop_index("ix_recipe_ingredients_recipe_id", table_name="recipe_ingredients")
    op.drop_table("recipe_ingredients")

    op.drop_index("ix_recipe_steps_recipe_id", table_name="recipe_steps")
    op.drop_table("recipe_steps")

    op.drop_index("ix_recipes_public", table_name="recipes")
    op.drop_index("ix_recipes_difficulty_id", table_name="recipes")
    op.drop_index("ix_recipes_category_id", table_name="recipes")
    op.drop_index("ix_recipes_source_recipe_id", table_name="recipes")
    op.drop_index("ix_recipes_created_by_user_id", table_name="recipes")
    op.drop_table("recipes")

    op.drop_table("difficulties")
    op.drop_table("recipe_categories")
