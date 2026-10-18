"""
expand recipe taxonomy: 14 categories, 28 grouped tags

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-18

Approved catalog. Existing rows are renamed in place (ids preserved), so no
recipe loses its category or tags, except the removed "Para regalar" tag,
whose recipe links are dropped with it.
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------- categories
_RENAMED_CATEGORIES = [("Panes y masas", "Panes dulces")]
_NEW_CATEGORIES = [
    "Cheesecakes",
    "Alfajores",
    "Masas hojaldradas",
    "Flanes y cremas",
    "Donas y frituras",
    "Rellenos y coberturas",
]
# On downgrade, recipes in a removed category go back to the closest old one (None = uncategorized).
_DOWNGRADE_CATEGORY_FALLBACK = {
    "Cheesecakes": "Tortas",
    "Alfajores": "Galletas",
    "Masas hojaldradas": "Panes y masas",
    "Flanes y cremas": "Postres fríos",
    "Donas y frituras": None,
    "Rellenos y coberturas": None,
}

# ---------------------------------------------------------------- tags
_RENAMED_TAGS = [("Rápida", "Rápida (menos de 30 min)")]
_REMOVED_TAGS = ["Para regalar"]
_TAGS_BY_GROUP = {
    "sabor": [
        "Chocolate", "Vainilla", "Frutal", "Cítricos", "Frutos secos", "Café", "Coco", "Manjar blanco", "Especias",
    ],
    "dieta": ["Sin gluten", "Sin lactosa", "Sin huevo", "Vegana", "Sin azúcar añadida"],
    "tecnica": ["Sin horno", "En microondas", "En freidora de aire", "Sin batidora"],
    "tiempo": ["Rápida (menos de 30 min)", "Requiere reposo", "Se prepara con anticipación"],
    "celebraciones": [
        "Cumpleaños", "Navidad", "Pascua", "San Valentín", "Día de la Madre", "Fiestas Patrias", "Halloween",
    ],
}
_TAGS_BEFORE = [  # what 0010 seeded, to restore on downgrade
    "Chocolate", "Frutal", "Frutos secos", "Sin gluten", "Sin lactosa", "Vegana", "Sin azúcar añadida",
    "Sin horno", "Rápida", "Navidad", "Cumpleaños", "Para regalar",
]

_categories = sa.table("recipe_categories", sa.column("id"), sa.column("name"))
_tags = sa.table("tags", sa.column("id"), sa.column("name"), sa.column("tag_group"))
_recipe_tags = sa.table("recipe_tags", sa.column("tag_id"))
_recipes = sa.table("recipes", sa.column("category_id"))


def upgrade() -> None:
    connection = op.get_bind()

    # categories
    for old_name, new_name in _RENAMED_CATEGORIES:
        op.execute(_categories.update().where(_categories.c.name == old_name).values(name=new_name))
    op.bulk_insert(_categories, [{"id": uuid.uuid4(), "name": name} for name in _NEW_CATEGORIES])

    # tags: group column (nullable until every row has a group)
    op.add_column("tags", sa.Column("tag_group", sa.String(20), nullable=True))
    for old_name, new_name in _RENAMED_TAGS:
        op.execute(_tags.update().where(_tags.c.name == old_name).values(name=new_name))
    removed_ids = select_ids(connection, _REMOVED_TAGS)
    if removed_ids:
        op.execute(_recipe_tags.delete().where(_recipe_tags.c.tag_id.in_(removed_ids)))
        op.execute(_tags.delete().where(_tags.c.id.in_(removed_ids)))

    existing = {row.name for row in connection.execute(sa.select(_tags.c.name))}
    new_rows = []
    for group, names in _TAGS_BY_GROUP.items():
        for name in names:
            if name in existing:
                op.execute(_tags.update().where(_tags.c.name == name).values(tag_group=group))
            else:
                new_rows.append({"id": uuid.uuid4(), "name": name, "tag_group": group})
    op.bulk_insert(_tags, new_rows)

    op.alter_column("tags", "tag_group", nullable=False)
    op.create_check_constraint(
        "ck_tags_group", "tags", "tag_group IN ('sabor', 'dieta', 'tecnica', 'tiempo', 'celebraciones')"
    )


def downgrade() -> None:
    connection = op.get_bind()

    # tags
    keep = set(_TAGS_BEFORE) | {new for _, new in _RENAMED_TAGS}
    all_names = [name for names in _TAGS_BY_GROUP.values() for name in names]
    dropped_ids = select_ids(connection, [name for name in all_names if name not in keep])
    if dropped_ids:
        op.execute(_recipe_tags.delete().where(_recipe_tags.c.tag_id.in_(dropped_ids)))
        op.execute(_tags.delete().where(_tags.c.id.in_(dropped_ids)))
    for old_name, new_name in _RENAMED_TAGS:
        op.execute(_tags.update().where(_tags.c.name == new_name).values(name=old_name))
    op.drop_constraint("ck_tags_group", "tags", type_="check")
    op.drop_column("tags", "tag_group")
    restored = sa.table("tags", sa.column("id"), sa.column("name"))
    op.bulk_insert(restored, [{"id": uuid.uuid4(), "name": name} for name in _REMOVED_TAGS])

    # categories
    for old_name, new_name in _RENAMED_CATEGORIES:
        op.execute(_categories.update().where(_categories.c.name == new_name).values(name=old_name))
    for name, fallback in _DOWNGRADE_CATEGORY_FALLBACK.items():
        fallback_id = (
            sa.select(_categories.c.id).where(_categories.c.name == fallback).scalar_subquery() if fallback else None
        )
        category_id = sa.select(_categories.c.id).where(_categories.c.name == name).scalar_subquery()
        op.execute(_recipes.update().where(_recipes.c.category_id == category_id).values(category_id=fallback_id))
    op.execute(_categories.delete().where(_categories.c.name.in_(_NEW_CATEGORIES)))


def select_ids(connection, names: list[str]) -> list:
    return [row.id for row in connection.execute(sa.select(_tags.c.id).where(_tags.c.name.in_(names)))]
