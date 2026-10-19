"""seed 50 more pastry ingredients (catalog 62 -> 112), in Spanish and English, with weight figures

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-19

Weights per measure come from King Arthur Baking's ingredient weight chart,
USDA FoodData Central (fruits, juices, dairy) and the tables of
tartademanzanacasera.com. Where the sources did not agree or had no figure,
none is seeded: the converter then says it has no weight for that
ingredient instead of guessing.

Idempotent against real data: an ingredient is skipped if any existing
ingredient already uses one of its names in any language (users may have
created it), and nothing existing is modified.
"""
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

# (Spanish, English, category code, {unit abbreviation: grams for 1 of it})
_INGREDIENTS = [
    ("Huevo", "Egg", "lácteo", {}),
    ("Esencia de vainilla", "Vanilla extract", "esencia", {"tbsp": "13", "tsp": "4.2"}),
    ("Esencia de almendra", "Almond extract", "esencia", {"tsp": "4.2"}),
    ("Agua", "Water", "otro", {"cup": "236"}),
    ("Chocolate blanco, chips", "White chocolate chips", "otro", {"cup": "170"}),
    ("Harina de maíz (polenta)", "Cornmeal", "harina", {"cup": "138"}),
    ("Harina leudante", "Self-rising flour", "harina", {"cup": "113"}),
    ("Harina de centeno", "Rye flour", "harina", {"cup": "102"}),
    ("Harina de trigo sarraceno", "Buckwheat flour", "harina", {"cup": "120"}),
    ("Fécula de mandioca", "Tapioca starch", "harina", {"cup": "113"}),
    ("Harina de arroz", "Rice flour", "harina", {}),
    ("Glucosa (jarabe de maíz)", "Corn syrup", "endulzante", {"cup": "328", "tbsp": "20.5"}),
    ("Jarabe de arce", "Maple syrup", "endulzante", {"cup": "322", "tbsp": "20"}),
    ("Suero de leche", "Buttermilk", "lácteo", {"cup": "242"}),
    ("Leche evaporada", "Evaporated milk", "lácteo", {"cup": "253"}),
    ("Mascarpone", "Mascarpone", "lácteo", {"cup": "227"}),
    ("Ricota", "Ricotta", "lácteo", {"cup": "246"}),
    ("Leche de almendras", "Almond milk", "lácteo", {"cup": "240"}),
    ("Margarina", "Margarine", "grasa", {"cup": "227", "tbsp": "14"}),
    ("Grasa vegetal", "Vegetable shortening", "grasa", {"cup": "190"}),
    ("Pistachos, enteros", "Pistachios, whole", "fruto seco", {"cup": "128"}),
    ("Maní, entero", "Peanuts, whole", "fruto seco", {"cup": "141"}),
    ("Almendras fileteadas", "Sliced almonds", "fruto seco", {"cup": "92"}),
    ("Semillas de chía", "Chia seeds", "otro", {"cup": "170", "tbsp": "12"}),
    ("Semillas de lino", "Flaxseeds", "otro", {}),
    ("Semillas de amapola", "Poppy seeds", "otro", {}),
    ("Frutillas, en rodajas", "Strawberries, sliced", "fruta", {"cup": "166"}),
    ("Moras, frescas", "Blackberries, fresh", "fruta", {"cup": "144"}),
    ("Cerezas, descarozadas", "Cherries, pitted", "fruta", {"cup": "154"}),
    ("Jugo de limón", "Lemon juice", "fruta", {"cup": "244", "tbsp": "15"}),
    ("Jugo de naranja", "Orange juice", "fruta", {"cup": "248", "tbsp": "15.5"}),
    ("Higos secos, picados", "Dried figs, chopped", "fruta", {"cup": "149"}),
    ("Damascos secos", "Dried apricots", "fruta", {"cup": "130"}),
    ("Puré de calabaza", "Pumpkin purée", "otro", {"cup": "245"}),
    ("Mermelada", "Jam", "otro", {"cup": "320", "tbsp": "20"}),
    ("Crema de avellanas y cacao", "Chocolate hazelnut spread", "otro", {"tbsp": "18.5"}),
    ("Café preparado", "Brewed coffee", "otro", {"cup": "237"}),
    ("Café instantáneo", "Instant coffee", "otro", {}),
    ("Vinagre", "Vinegar", "otro", {"tbsp": "15"}),
    ("Dulce de membrillo", "Quince paste", "otro", {}),
    ("Dulce de batata", "Sweet potato paste", "otro", {}),
    ("Levadura fresca", "Fresh yeast", "leudante", {}),
    ("Levadura instantánea", "Instant yeast", "leudante", {"tbsp": "9", "tsp": "3"}),
    ("Masa madre", "Sourdough starter", "leudante", {}),
    ("Cremor tártaro", "Cream of tartar", "leudante", {"tsp": "3"}),
    ("Nuez moscada molida", "Ground nutmeg", "especia", {"tsp": "2.2"}),
    ("Jengibre molido", "Ground ginger", "especia", {"tsp": "1.8"}),
    ("Clavo de olor molido", "Ground cloves", "especia", {"tsp": "2.1"}),
    ("Cardamomo molido", "Ground cardamom", "especia", {"tsp": "2"}),
    ("Azúcar de coco", "Coconut sugar", "azúcar", {}),
]


def upgrade() -> None:
    bind = op.get_bind()
    units = dict(bind.execute(sa.text("SELECT abbreviation, id FROM units")).all())
    taken = sa.text(
        "SELECT 1 FROM ingredients WHERE lower(names->>'es') IN (lower(:es), lower(:en)) "
        "OR lower(names->>'en') IN (lower(:es), lower(:en)) LIMIT 1"
    )
    insert_ingredient = sa.text(
        "INSERT INTO ingredients (id, names, name_language, default_category) "
        "VALUES (:id, CAST(:names AS jsonb), 'es', :category)"
    )
    insert_conversion = sa.text(
        "INSERT INTO ingredient_unit_conversions (id, ingredient_id, unit_id, grams_equivalent) "
        "VALUES (:id, :ingredient_id, :unit_id, CAST(:grams AS numeric))"
    )
    for spanish, english, category, grams in _INGREDIENTS:
        if bind.execute(taken, {"es": spanish, "en": english}).first():
            continue
        ingredient_id = uuid.uuid4()
        names = json.dumps({"es": spanish, "en": english}, ensure_ascii=False)
        bind.execute(insert_ingredient, {"id": ingredient_id, "names": names, "category": category})
        for abbreviation, value in grams.items():
            bind.execute(
                insert_conversion,
                {"id": uuid.uuid4(), "ingredient_id": ingredient_id, "unit_id": units[abbreviation], "grams": value},
            )


def downgrade() -> None:
    bind = op.get_bind()
    for spanish, _english, _category, _grams in _INGREDIENTS:
        # Only rows nobody references, so a downgrade never breaks a recipe or a pantry.
        bind.execute(
            sa.text(
                """
                DELETE FROM ingredients i
                WHERE i.names->>'es' = :es
                  AND NOT EXISTS (SELECT 1 FROM recipe_ingredients r WHERE r.ingredient_id = i.id)
                  AND NOT EXISTS (SELECT 1 FROM user_ingredients u WHERE u.ingredient_id = i.id)
                """
            ),
            {"es": spanish},
        )

