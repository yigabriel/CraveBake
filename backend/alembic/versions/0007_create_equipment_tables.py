"""
create equipment and user_equipment tables + seed common pastry equipment

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-18
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# (name, equipment_type)
_SEED_EQUIPMENT = [
    ("Molde redondo desmontable", "molde"),
    ("Molde rectangular", "molde"),
    ("Molde para budín", "molde"),
    ("Molde para tarta", "molde"),
    ("Molde para cupcakes y muffins", "molde"),
    ("Molde bundt (savarín)", "molde"),
    ("Bandeja para horno", "molde"),
    ("Batidor de globo", "utensilio"),
    ("Espátula de silicona", "utensilio"),
    ("Rodillo", "utensilio"),
    ("Manga pastelera", "utensilio"),
    ("Tamiz", "utensilio"),
    ("Balanza de cocina", "utensilio"),
    ("Tazas y cucharas medidoras", "utensilio"),
    ("Rejilla de enfriado", "utensilio"),
    ("Bowl", "utensilio"),
    ("Horno", "electrodomestico"),
    ("Batidora de mano", "electrodomestico"),
    ("Batidora planetaria", "electrodomestico"),
    ("Procesadora de alimentos", "electrodomestico"),
    ("Microondas", "electrodomestico"),
    ("Termómetro de cocina", "otro"),
    ("Soplete de cocina", "otro"),
]


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    equipment_table = op.create_table(
        "equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("equipment_type", sa.String(20), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        *_timestamp_columns(),
        sa.CheckConstraint(
            "equipment_type IN ('molde', 'utensilio', 'electrodomestico', 'otro')", name="ck_equipment_type"
        ),
    )

    op.create_table(
        "user_equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("equipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("equipment.id"), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("notes", sa.String(500), nullable=True),
        *_timestamp_columns(),
        sa.UniqueConstraint("user_id", "equipment_id", name="uq_user_equipment"),
        sa.CheckConstraint("quantity >= 1", name="ck_user_equipment_quantity"),
    )
    op.create_index("ix_user_equipment_user_id", "user_equipment", ["user_id"])

    op.bulk_insert(
        equipment_table,
        [
            {"id": uuid.uuid4(), "name": name, "equipment_type": equipment_type}
            for name, equipment_type in _SEED_EQUIPMENT
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_user_equipment_user_id", table_name="user_equipment")
    op.drop_table("user_equipment")
    op.drop_table("equipment")
