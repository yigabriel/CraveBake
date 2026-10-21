"""English as the base: stable codes in English, and English as the original language of the catalog

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-21

1. The stable codes that the API exposes and filters by were Spanish ("harina",
   "molde", "sabor"). They become English ("flour", "mold", "flavor"). The
   Spanish words stay as the Spanish translation of each name.
2. The catalog was seeded in Spanish, so its `name_language` (the language a
   name was originally written in, used as the fallback) was "es". It becomes
   "en" for every row that has an English name. A row that only has a Spanish
   name (created by a user, never translated) keeps "es": it really was written
   in Spanish, and switching it would show a Spanish name as if it were English.

Pure data change plus the two CHECK constraints: nothing is dropped or merged.
"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

_INGREDIENT_CATEGORIES = {
    "harina": "flour",
    "azúcar": "sugar",
    "endulzante": "sweetener",
    "grasa": "fat",
    "lácteo": "dairy",
    "leudante": "leavener",
    "fruta": "fruit",
    "fruto seco": "nut",
    "especia": "spice",
    "esencia": "extract",
    "otro": "other",
}
_EQUIPMENT_TYPES = {"molde": "mold", "utensilio": "utensil", "electrodomestico": "appliance", "otro": "other"}
_TAG_GROUPS = {
    "sabor": "flavor",
    "dieta": "diet",
    "tecnica": "technique",
    "tiempo": "time",
    "celebraciones": "celebrations",
}
# Every table whose names are a LocalizedText (`names` + `name_language`).
_LOCALIZED_TABLES = (
    "ingredients",
    "ingredient_categories",
    "equipment",
    "recipe_categories",
    "difficulties",
    "units",
    "tags",
)


def _recode(table: str, column: str, mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        op.execute(sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old").bindparams(old=old, new=new))


def _quoted(values) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    # The CHECK constraints reject the new values: drop them, recode, add them back.
    op.drop_constraint("ck_equipment_type", "equipment", type_="check")
    op.drop_constraint("ck_tags_group", "tags", type_="check")

    _recode("ingredients", "default_category", _INGREDIENT_CATEGORIES)
    _recode("ingredient_categories", "code", _INGREDIENT_CATEGORIES)
    _recode("equipment", "equipment_type", _EQUIPMENT_TYPES)
    _recode("tags", "tag_group", _TAG_GROUPS)

    op.create_check_constraint("ck_equipment_type", "equipment", f"equipment_type IN ({_quoted(_EQUIPMENT_TYPES.values())})")
    op.create_check_constraint("ck_tags_group", "tags", f"tag_group IN ({_quoted(_TAG_GROUPS.values())})")

    for table in _LOCALIZED_TABLES:
        op.execute(f"UPDATE {table} SET name_language = 'en' WHERE name_language = 'es' AND names ? 'en'")
        op.alter_column(table, "name_language", server_default="en")


def downgrade() -> None:
    for table in _LOCALIZED_TABLES:
        op.alter_column(table, "name_language", server_default="es")
        # Only the rows that have a Spanish name can go back to it.
        op.execute(f"UPDATE {table} SET name_language = 'es' WHERE name_language = 'en' AND names ? 'es'")

    op.drop_constraint("ck_equipment_type", "equipment", type_="check")
    op.drop_constraint("ck_tags_group", "tags", type_="check")

    _recode("ingredients", "default_category", {new: old for old, new in _INGREDIENT_CATEGORIES.items()})
    _recode("ingredient_categories", "code", {new: old for old, new in _INGREDIENT_CATEGORIES.items()})
    _recode("equipment", "equipment_type", {new: old for old, new in _EQUIPMENT_TYPES.items()})
    _recode("tags", "tag_group", {new: old for old, new in _TAG_GROUPS.items()})

    op.create_check_constraint("ck_equipment_type", "equipment", f"equipment_type IN ({_quoted(_EQUIPMENT_TYPES)})")
    op.create_check_constraint("ck_tags_group", "tags", f"tag_group IN ({_quoted(_TAG_GROUPS)})")
