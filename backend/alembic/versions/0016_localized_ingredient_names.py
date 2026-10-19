"""localized ingredient names: ingredients.name -> names (JSONB) + name_language, with English for the catalog

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-19

- ingredients.name (one Spanish string) becomes names = {"es": ..., "en": ...}
  plus name_language (the language it was written in, the fallback).
- The 62 seeded ingredients (0003) get their English name.
- Names stay unique per language ignoring case (expression indexes).
- preparation_ingredients keeps a snapshot of every language too, so the
  cooking history follows the viewer's language.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

# Seeded Spanish name (0003) -> English. Argentine terms: manteca = butter, 0000 = all-purpose.
_ENGLISH = {
    "Aceite": "Vegetable oil",
    "Aceite de coco": "Coconut oil",
    "Aceite de oliva": "Olive oil",
    "Almendras, enteras": "Almonds, whole",
    "Avellanas, enteras": "Hazelnuts, whole",
    "Arándanos, frescos": "Blueberries, fresh",
    "Arándanos, secos": "Dried cranberries",
    "Azúcar blanca": "Granulated sugar",
    "Azúcar impalpable": "Powdered sugar",
    "Azúcar rubia": "Light brown sugar",
    "Azúcar mascabado": "Muscovado sugar",
    "Banana, majada": "Banana, mashed",
    "Banana, rebanada": "Banana, sliced",
    "Bicarbonato de sodio": "Baking soda",
    "Cacao en polvo": "Cocoa powder",
    "Canela molida": "Ground cinnamon",
    "Chocolate, chips": "Chocolate chips",
    "Chocolate, en trozos": "Chocolate, chopped",
    "Coco rallado": "Shredded coconut",
    "Copos de avena": "Rolled oats",
    "Crema agria": "Sour cream",
    "Crema de leche": "Heavy cream",
    "Dátiles, enteros": "Dates, whole",
    "Dátiles, descarozados": "Dates, pitted",
    "Dulce de leche": "Dulce de leche",
    "Frambuesas, frescas": "Raspberries, fresh",
    "Galletas molidas": "Cookie crumbs",
    "Gelatina sin sabor": "Unflavored gelatin",
    "Harina panificable (000)": "Bread flour",
    "Harina todo uso (0000)": "All-purpose flour",
    "Harina integral": "Whole wheat flour",
    "Harina de almendra": "Almond flour",
    "Harina de avena": "Oat flour",
    "Harina de coco": "Coconut flour",
    "Huevo, clara": "Egg white",
    "Huevo, yema": "Egg yolk",
    "Leche": "Milk",
    "Leche condensada": "Sweetened condensed milk",
    "Leche de coco": "Coconut milk",
    "Levadura seca": "Dry yeast",
    "Maicena": "Cornstarch",
    "Manteca": "Butter",
    "Mantequilla de maní": "Peanut butter",
    "Manzana, picada": "Apple, chopped",
    "Manzana, rallada": "Apple, grated",
    "Melaza": "Molasses",
    "Miel": "Honey",
    "Nueces, en mitades": "Walnut halves",
    "Pecanas, en mitades": "Pecan halves",
    "Pasas de uva": "Raisins",
    "Pasta de dátiles": "Date paste",
    "Polvo de hornear": "Baking powder",
    "Puré de manzana": "Applesauce",
    "Queso crema": "Cream cheese",
    "Ralladura": "Citrus zest",
    "Remolacha, rallada": "Beet, grated",
    "Sal": "Salt",
    "Salvado de avena": "Oat bran",
    "Semillas de sésamo": "Sesame seeds",
    "Yogurt": "Yogurt",
    "Yogurt griego": "Greek yogurt",
    "Zanahoria rallada": "Carrot, grated",
}
_LANGUAGES = ("es", "en")


def _fail_on_case_duplicates(language: str) -> None:
    duplicates = op.get_bind().execute(
        sa.text(
            f"SELECT lower(names->>'{language}') AS name, count(*) FROM ingredients "
            f"WHERE names ? '{language}' GROUP BY 1 HAVING count(*) > 1"
        )
    ).all()
    if duplicates:
        listed = ", ".join(f"{name!r} x{count}" for name, count in duplicates)
        raise RuntimeError(
            f"Ingredients whose '{language}' names differ only in case: {listed}. "
            "Merge or rename them (and their recipe/pantry references) before running this migration."
        )


def upgrade() -> None:
    op.add_column("ingredients", sa.Column("names", postgresql.JSONB(), nullable=True))
    op.add_column("ingredients", sa.Column("name_language", sa.String(2), nullable=False, server_default="es"))
    op.execute("UPDATE ingredients SET names = jsonb_build_object('es', name)")

    english = sa.text("UPDATE ingredients SET names = names || jsonb_build_object('en', CAST(:en AS text)) WHERE name = :es")
    for spanish, en in _ENGLISH.items():
        op.execute(english.bindparams(es=spanish, en=en))

    op.alter_column("ingredients", "names", nullable=False)
    op.drop_index("ix_ingredients_name", table_name="ingredients")
    op.drop_constraint("ingredients_name_key", "ingredients", type_="unique")
    op.drop_column("ingredients", "name")

    for language in _LANGUAGES:
        _fail_on_case_duplicates(language)
        op.execute(f"CREATE UNIQUE INDEX ux_ingredients_name_{language} ON ingredients (lower(names->>'{language}'))")

    # Cooking history: snapshot every language of the ingredient's current name.
    op.add_column("preparation_ingredients", sa.Column("ingredient_names", postgresql.JSONB(), nullable=True))
    op.add_column("preparation_ingredients", sa.Column("ingredient_name_language", sa.String(2), nullable=True))
    op.execute(
        """
        UPDATE preparation_ingredients AS p
        SET ingredient_names = i.names, ingredient_name_language = i.name_language
        FROM ingredients AS i
        WHERE i.id = p.ingredient_id
        """
    )
    op.execute(
        """
        UPDATE preparation_ingredients
        SET ingredient_names = jsonb_build_object('es', ingredient_name), ingredient_name_language = 'es'
        WHERE ingredient_names IS NULL AND ingredient_name IS NOT NULL
        """
    )
    op.drop_column("preparation_ingredients", "ingredient_name")


def downgrade() -> None:
    op.add_column("preparation_ingredients", sa.Column("ingredient_name", sa.String(255), nullable=True))
    op.execute(
        "UPDATE preparation_ingredients SET ingredient_name = ingredient_names->>coalesce(ingredient_name_language, 'es')"
    )
    op.drop_column("preparation_ingredients", "ingredient_name_language")
    op.drop_column("preparation_ingredients", "ingredient_names")

    for language in _LANGUAGES:
        op.execute(f"DROP INDEX ux_ingredients_name_{language}")
    op.add_column("ingredients", sa.Column("name", sa.String(255), nullable=True))
    op.execute("UPDATE ingredients SET name = names->>name_language")
    op.alter_column("ingredients", "name", nullable=False)
    op.create_unique_constraint("ingredients_name_key", "ingredients", ["name"])
    op.create_index("ix_ingredients_name", "ingredients", ["name"])
    op.drop_column("ingredients", "name_language")
    op.drop_column("ingredients", "names")
