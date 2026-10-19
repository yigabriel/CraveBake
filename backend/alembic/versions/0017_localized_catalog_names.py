"""localized names for every other catalog + ingredient category names

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-19

Same shape as ingredients (0016): `name` becomes `names` (JSONB, language ->
text) plus `name_language`, with English for every seeded row, in:
equipment, recipe_categories, difficulties, tags and units.

Ingredient categories were free text on each ingredient ("harina"). That text
stays as a stable code, and the new `ingredient_categories` table names each
code per language ("Harinas" / "Flours").
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_LANGUAGES = ("es", "en")

# table -> (old unique constraint or None, old column length, {seeded Spanish name: English})
_CATALOGS = {
    "equipment": ("equipment_name_key", 150, {
        "Molde redondo desmontable": "Springform pan",
        "Molde rectangular": "Rectangular pan",
        "Molde para budín": "Loaf pan",
        "Molde para tarta": "Tart pan",
        "Molde para cupcakes y muffins": "Muffin tin",
        "Molde bundt (savarín)": "Bundt pan",
        "Bandeja para horno": "Baking sheet",
        "Batidor de globo": "Balloon whisk",
        "Espátula de silicona": "Silicone spatula",
        "Rodillo": "Rolling pin",
        "Manga pastelera": "Piping bag",
        "Tamiz": "Sifter",
        "Balanza de cocina": "Kitchen scale",
        "Tazas y cucharas medidoras": "Measuring cups & spoons",
        "Rejilla de enfriado": "Cooling rack",
        "Bowl": "Mixing bowl",
        "Horno": "Oven",
        "Batidora de mano": "Hand mixer",
        "Batidora planetaria": "Stand mixer",
        "Procesadora de alimentos": "Food processor",
        "Microondas": "Microwave",
        "Termómetro de cocina": "Kitchen thermometer",
        "Soplete de cocina": "Kitchen torch",
    }),
    "recipe_categories": ("recipe_categories_name_key", 100, {
        "Alfajores": "Alfajores",
        "Brownies y barras": "Brownies & bars",
        "Cheesecakes": "Cheesecakes",
        "Cupcakes": "Cupcakes",
        "Donas y frituras": "Donuts & fried treats",
        "Flanes y cremas": "Flans & custards",
        "Galletas": "Cookies",
        "Masas hojaldradas": "Puff & laminated pastry",
        "Muffins": "Muffins",
        "Panes dulces": "Sweet breads",
        "Postres fríos": "Chilled desserts",
        "Rellenos y coberturas": "Fillings & frostings",
        "Tartas y pies": "Tarts & pies",
        "Tortas": "Cakes",
    }),
    "difficulties": ("difficulties_name_key", 50, {"Fácil": "Easy", "Intermedio": "Intermediate", "Difícil": "Hard"}),
    "tags": ("tags_name_key", 60, {
        "Café": "Coffee",
        "Chocolate": "Chocolate",
        "Coco": "Coconut",
        "Cítricos": "Citrus",
        "Especias": "Spiced",
        "Frutal": "Fruity",
        "Frutos secos": "Nuts",
        "Manjar blanco": "Manjar (milk caramel)",
        "Vainilla": "Vanilla",
        "Sin azúcar añadida": "No added sugar",
        "Sin gluten": "Gluten-free",
        "Sin huevo": "Egg-free",
        "Sin lactosa": "Lactose-free",
        "Vegana": "Vegan",
        "En freidora de aire": "Air fryer",
        "En microondas": "Microwave",
        "Sin batidora": "No mixer",
        "Sin horno": "No-bake",
        "Requiere reposo": "Needs resting time",
        "Rápida (menos de 30 min)": "Quick (under 30 min)",
        "Se prepara con anticipación": "Make ahead",
        "Cumpleaños": "Birthday",
        "Día de la Madre": "Mother's Day",
        "Fiestas Patrias": "National holidays",
        "Halloween": "Halloween",
        "Navidad": "Christmas",
        "Pascua": "Easter",
        "San Valentín": "Valentine's Day",
    }),
    "units": (None, 50, {
        "gramo": "gram",
        "kilogramo": "kilogram",
        "onza": "ounce",
        "mililitro": "milliliter",
        "litro": "liter",
        "taza": "cup",
        "cucharada": "tablespoon",
        "cucharadita": "teaspoon",
        "unidad": "unit",
    }),
}

# Ingredient category code (what ingredients.default_category holds) -> names.
_INGREDIENT_CATEGORIES = {
    "harina": ("Harinas y almidones", "Flours & starches"),
    "azúcar": ("Azúcares", "Sugars"),
    "endulzante": ("Mieles y jarabes", "Syrups & honey"),
    "grasa": ("Grasas y aceites", "Fats & oils"),
    "lácteo": ("Lácteos y huevos", "Dairy & eggs"),
    "leudante": ("Leudantes", "Leaveners"),
    "fruta": ("Frutas", "Fruits"),
    "fruto seco": ("Frutos secos", "Nuts"),
    "especia": ("Especias", "Spices"),
    "esencia": ("Esencias y extractos", "Extracts"),
    "otro": ("Otros", "Other"),
}


def _fail_on_case_duplicates(table: str, language: str) -> None:
    duplicates = op.get_bind().execute(
        sa.text(
            f"SELECT lower(names->>'{language}'), count(*) FROM {table} "
            f"WHERE names ? '{language}' GROUP BY 1 HAVING count(*) > 1"
        )
    ).all()
    if duplicates:
        listed = ", ".join(f"{name!r} x{count}" for name, count in duplicates)
        raise RuntimeError(f"{table}: '{language}' names that differ only in case: {listed}. Merge or rename them first.")


def _localize(table: str, unique_constraint: str | None, english: dict[str, str]) -> None:
    op.add_column(table, sa.Column("names", postgresql.JSONB(), nullable=True))
    op.add_column(table, sa.Column("name_language", sa.String(2), nullable=False, server_default="es"))
    op.execute(f"UPDATE {table} SET names = jsonb_build_object('es', name)")
    add_english = sa.text(f"UPDATE {table} SET names = names || jsonb_build_object('en', CAST(:en AS text)) WHERE name = :es")
    for spanish, en in english.items():
        op.execute(add_english.bindparams(es=spanish, en=en))
    op.alter_column(table, "names", nullable=False)
    if unique_constraint:
        op.drop_constraint(unique_constraint, table, type_="unique")
    op.drop_column(table, "name")
    if unique_constraint:
        for language in _LANGUAGES:
            _fail_on_case_duplicates(table, language)
            op.execute(f"CREATE UNIQUE INDEX ux_{table}_name_{language} ON {table} (lower(names->>'{language}'))")


def _restore(table: str, unique_constraint: str | None, length: int) -> None:
    if unique_constraint:
        for language in _LANGUAGES:
            op.execute(f"DROP INDEX ux_{table}_name_{language}")
    op.add_column(table, sa.Column("name", sa.String(length), nullable=True))
    op.execute(f"UPDATE {table} SET name = names->>name_language")
    op.alter_column(table, "name", nullable=False)
    if unique_constraint:
        op.create_unique_constraint(unique_constraint, table, ["name"])
    op.drop_column(table, "name_language")
    op.drop_column(table, "names")


def upgrade() -> None:
    for table, (constraint, _length, english) in _CATALOGS.items():
        _localize(table, constraint, english)

    categories = op.create_table(
        "ingredient_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("names", postgresql.JSONB(), nullable=False),
        sa.Column("name_language", sa.String(2), nullable=False, server_default="es"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.bulk_insert(
        categories,
        [
            {"id": uuid.uuid4(), "code": code, "names": {"es": es, "en": en}, "name_language": "es"}
            for code, (es, en) in _INGREDIENT_CATEGORIES.items()
        ],
    )


def downgrade() -> None:
    op.drop_table("ingredient_categories")
    for table, (constraint, length, _english) in _CATALOGS.items():
        _restore(table, constraint, length)
