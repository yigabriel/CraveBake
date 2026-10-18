"""seed common pastry ingredients with real cup/tbsp/tsp -> grams conversions

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-02

Source: https://www.bakeandshare.com/blog/tablas-conversiones-medidas/

This is the data that makes /converter actually useful: 1 cup of flour and
1 cup of powdered sugar are NOT the same weight, and a tablespoon figure is
not always a clean 1/16 of the cup figure either (these are practical,
rounded kitchen numbers, not a derived ratio) — which is exactly why
`ingredient_unit_conversions` stores one row per (ingredient, unit) pair
instead of a single factor per ingredient.
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# (name, default_category)
_INGREDIENTS = [
    ("Aceite", "grasa"),
    ("Aceite de coco", "grasa"),
    ("Aceite de oliva", "grasa"),
    ("Almendras, enteras", "fruto seco"),
    ("Avellanas, enteras", "fruto seco"),
    ("Arándanos, frescos", "fruta"),
    ("Arándanos, secos", "fruta"),
    ("Azúcar blanca", "azúcar"),
    ("Azúcar impalpable", "azúcar"),
    ("Azúcar rubia", "azúcar"),
    ("Azúcar mascabado", "azúcar"),
    ("Banana, majada", "fruta"),
    ("Banana, rebanada", "fruta"),
    ("Bicarbonato de sodio", "leudante"),
    ("Cacao en polvo", "otro"),
    ("Canela molida", "especia"),
    ("Chocolate, chips", "otro"),
    ("Chocolate, en trozos", "otro"),
    ("Coco rallado", "otro"),
    ("Copos de avena", "harina"),
    ("Crema agria", "lácteo"),
    ("Crema de leche", "lácteo"),
    ("Dátiles, enteros", "fruta"),
    ("Dátiles, descarozados", "fruta"),
    ("Dulce de leche", "otro"),
    ("Frambuesas, frescas", "fruta"),
    ("Galletas molidas", "otro"),
    ("Gelatina sin sabor", "otro"),
    ("Harina panificable (000)", "harina"),
    ("Harina todo uso (0000)", "harina"),
    ("Harina integral", "harina"),
    ("Harina de almendra", "harina"),
    ("Harina de avena", "harina"),
    ("Harina de coco", "harina"),
    ("Huevo, clara", "lácteo"),
    ("Huevo, yema", "lácteo"),
    ("Leche", "lácteo"),
    ("Leche condensada", "lácteo"),
    ("Leche de coco", "lácteo"),
    ("Levadura seca", "leudante"),
    ("Maicena", "harina"),
    ("Manteca", "grasa"),
    ("Mantequilla de maní", "otro"),
    ("Manzana, picada", "fruta"),
    ("Manzana, rallada", "fruta"),
    ("Melaza", "endulzante"),
    ("Miel", "endulzante"),
    ("Nueces, en mitades", "fruto seco"),
    ("Pecanas, en mitades", "fruto seco"),
    ("Pasas de uva", "fruta"),
    ("Pasta de dátiles", "fruta"),
    ("Polvo de hornear", "leudante"),
    ("Puré de manzana", "fruta"),
    ("Queso crema", "lácteo"),
    ("Ralladura", "especia"),
    ("Remolacha, rallada", "otro"),
    ("Sal", "otro"),
    ("Salvado de avena", "harina"),
    ("Semillas de sésamo", "otro"),
    ("Yogurt", "lácteo"),
    ("Yogurt griego", "lácteo"),
    ("Zanahoria rallada", "otro"),
]

# 1 taza (cup) -> gramos
_CUP_GRAMS = {
    "Aceite": "225",
    "Aceite de coco": "220",
    "Aceite de oliva": "220",
    "Almendras, enteras": "150",
    "Avellanas, enteras": "130",
    "Arándanos, frescos": "150",
    "Arándanos, secos": "150",
    "Azúcar blanca": "200",
    "Azúcar impalpable": "115",
    "Azúcar rubia": "200",
    "Azúcar mascabado": "200",
    "Banana, majada": "250",
    "Banana, rebanada": "150",
    "Cacao en polvo": "82",
    "Chocolate, chips": "170",
    "Chocolate, en trozos": "140",
    "Coco rallado": "95",
    "Copos de avena": "80",
    "Crema agria": "240",
    "Crema de leche": "240",
    "Dátiles, enteros": "225",
    "Dátiles, descarozados": "175",
    "Dulce de leche": "300",
    "Frambuesas, frescas": "120",
    "Galletas molidas": "85",
    "Harina panificable (000)": "135",
    "Harina todo uso (0000)": "125",
    "Harina integral": "135",
    "Harina de almendra": "96",
    "Harina de avena": "90",
    "Harina de coco": "112",
    "Huevo, clara": "35",
    "Huevo, yema": "20",
    "Leche": "240",
    "Leche condensada": "305",
    "Leche de coco": "228",
    "Maicena": "112",
    "Manteca": "227",
    "Mantequilla de maní": "270",
    "Manzana, picada": "120",
    "Manzana, rallada": "135",
    "Melaza": "340",
    "Miel": "340",
    "Nueces, en mitades": "100",
    "Pecanas, en mitades": "100",
    "Pasas de uva": "160",
    "Pasta de dátiles": "300",
    "Puré de manzana": "245",
    "Queso crema": "227",
    "Remolacha, rallada": "135",
    "Salvado de avena": "80",
    "Semillas de sésamo": "150",
    "Yogurt": "240",
    "Yogurt griego": "280",
    "Zanahoria rallada": "135",
}

# 1 cucharada (tbsp) -> gramos. Solo para los ingredientes donde la fuente
# da una cifra dedicada de cucharada (distinta de dividir la taza entre 16).
_TBSP_GRAMS = {
    "Aceite de coco": "14",
    "Azúcar blanca": "12",
    "Bicarbonato de sodio": "12",
    "Canela molida": "8",
    "Cacao en polvo": "7.5",
    # NOTA: la fuente lista Gelatina sin sabor como 3g/cucharada y 9g/cucharadita,
    # lo cual es físicamente inconsistente (la cucharadita SIEMPRE es más chica
    # que la cucharada). Cada otro ingrediente de esta tabla sigue una relación
    # ~3:1 cucharada:cucharadita, así que este par casi seguro está invertido
    # en la fuente. Acá se usa el orden corregido (9g cucharada / 3g cucharadita).
    "Gelatina sin sabor": "9",
    "Harina todo uso (0000)": "9",
    "Levadura seca": "9",
    "Manteca": "14",
    "Mantequilla de maní": "15",
    "Miel": "21",
    "Polvo de hornear": "12",
    "Ralladura": "6",
    "Sal": "18",
}

# 1 cucharadita (tsp) -> gramos
_TSP_GRAMS = {
    "Aceite de coco": "4.7",
    "Azúcar blanca": "4",
    "Bicarbonato de sodio": "4",
    "Canela molida": "2.7",
    "Cacao en polvo": "3.7",
    "Gelatina sin sabor": "3",  # ver nota arriba
    "Harina todo uso (0000)": "3",
    "Levadura seca": "3",
    "Manteca": "4.7",
    "Mantequilla de maní": "5",
    "Miel": "7",
    "Polvo de hornear": "4",
    "Ralladura": "2",
    "Sal": "6",
}


def upgrade() -> None:
    bind = op.get_bind()

    ingredients_table = sa.table(
        "ingredients",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("default_category", sa.String),
    )
    conversions_table = sa.table(
        "ingredient_unit_conversions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("ingredient_id", postgresql.UUID(as_uuid=True)),
        sa.column("unit_id", postgresql.UUID(as_uuid=True)),
        sa.column("grams_equivalent", sa.Numeric),
    )
    units_table = sa.table(
        "units", sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("abbreviation", sa.String)
    )

    cup_id = bind.execute(sa.select(units_table.c.id).where(units_table.c.abbreviation == "cup")).scalar_one()
    tbsp_id = bind.execute(sa.select(units_table.c.id).where(units_table.c.abbreviation == "tbsp")).scalar_one()
    tsp_id = bind.execute(sa.select(units_table.c.id).where(units_table.c.abbreviation == "tsp")).scalar_one()

    ingredient_ids: dict[str, uuid.UUID] = {}
    for name, category in _INGREDIENTS:
        ingredient_id = uuid.uuid4()
        ingredient_ids[name] = ingredient_id
        bind.execute(ingredients_table.insert().values(id=ingredient_id, name=name, default_category=category))

    conversions = []
    for name, grams in _CUP_GRAMS.items():
        conversions.append(
            {"id": uuid.uuid4(), "ingredient_id": ingredient_ids[name], "unit_id": cup_id, "grams_equivalent": grams}
        )
    for name, grams in _TBSP_GRAMS.items():
        conversions.append(
            {"id": uuid.uuid4(), "ingredient_id": ingredient_ids[name], "unit_id": tbsp_id, "grams_equivalent": grams}
        )
    for name, grams in _TSP_GRAMS.items():
        conversions.append(
            {"id": uuid.uuid4(), "ingredient_id": ingredient_ids[name], "unit_id": tsp_id, "grams_equivalent": grams}
        )

    bind.execute(conversions_table.insert(), conversions)


def downgrade() -> None:
    bind = op.get_bind()
    names = [name for name, _ in _INGREDIENTS]
    bind.execute(
        sa.text(
            "DELETE FROM ingredient_unit_conversions WHERE ingredient_id IN "
            "(SELECT id FROM ingredients WHERE name = ANY(:names))"
        ),
        {"names": names},
    )
    bind.execute(sa.text("DELETE FROM ingredients WHERE name = ANY(:names)"), {"names": names})
