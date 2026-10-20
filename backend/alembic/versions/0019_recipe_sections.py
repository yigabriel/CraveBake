"""recipe sections: named groups of ingredient lines and steps ("Masa choux", "Manjar")

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-20

`recipe_sections` holds each group's name once; `recipe_ingredients` and
`recipe_steps` point to it with a nullable `section_id` (existing recipes
simply have no sections). Preparations keep their own copy of the name, like
they do for everything else they snapshot, so a finished preparation never
changes when its recipe does.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recipe_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("uq_recipe_sections_name", "recipe_sections", ["recipe_id", sa.text("lower(name)")], unique=True)

    for table in ("recipe_ingredients", "recipe_steps"):
        op.add_column(
            table,
            sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipe_sections.id", ondelete="SET NULL"), nullable=True),
        )
        # Deleting a section's lines must not scan the whole table.
        op.create_index(f"ix_{table}_section_id", table, ["section_id"])

    op.add_column("preparation_ingredients", sa.Column("section", sa.String(100), nullable=True))
    op.add_column("preparation_steps", sa.Column("section", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("preparation_steps", "section")
    op.drop_column("preparation_ingredients", "section")
    for table in ("recipe_steps", "recipe_ingredients"):
        op.drop_index(f"ix_{table}_section_id", table_name=table)
        op.drop_column(table, "section_id")
    op.drop_index("uq_recipe_sections_name", table_name="recipe_sections")
    op.drop_table("recipe_sections")
