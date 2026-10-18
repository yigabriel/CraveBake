"""
create user_saved_recipes table (favorites, portfolio bounded context)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-13

"Only public recipes of other users can be saved" lives in the
`SavedRecipe` entity, not in a trigger.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_saved_recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # No cascade: recipes are only ever soft-deleted.
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "recipe_id", name="uq_user_saved_recipe"),
    )
    op.create_index("ix_user_saved_recipes_user_id", "user_saved_recipes", ["user_id"])
    op.create_index("ix_user_saved_recipes_recipe_id", "user_saved_recipes", ["recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_user_saved_recipes_recipe_id", table_name="user_saved_recipes")
    op.drop_index("ix_user_saved_recipes_user_id", table_name="user_saved_recipes")
    op.drop_table("user_saved_recipes")
