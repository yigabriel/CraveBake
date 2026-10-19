"""In-memory test doubles for the ingredients ports, seeded with the real unit catalog."""
from __future__ import annotations

from decimal import Decimal

from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.entities.ingredient_unit_conversion import IngredientUnitConversion
from app.ingredients.domain.entities.unit import Unit, UnitSystem, UnitType
from app.ingredients.domain.entities.user_ingredient import UserIngredient
from app.ingredients.domain.repositories.ingredient_repository import IngredientRepository
from app.ingredients.domain.repositories.ingredient_unit_conversion_repository import (
    IngredientUnitConversionRepository,
)
from app.ingredients.domain.repositories.unit_repository import UnitRepository
from app.ingredients.domain.repositories.user_ingredient_repository import UserIngredientRepository
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.ingredient_unit_conversion_id import IngredientUnitConversionId
from app.ingredients.domain.value_objects.unit_id import UnitId
from app.shared.domain.value_objects.localized_text import LocalizedText

# Same rows as alembic 0002 (factors) + 0013 (unit systems).
_SEED_UNITS = [
    ("gramo", "g", UnitType.WEIGHT, "1", UnitSystem.METRIC),
    ("kilogramo", "kg", UnitType.WEIGHT, "1000", UnitSystem.METRIC),
    ("onza", "oz", UnitType.WEIGHT, "28.3495", UnitSystem.US),
    ("mililitro", "ml", UnitType.VOLUME, "1", UnitSystem.METRIC),
    ("litro", "l", UnitType.VOLUME, "1000", UnitSystem.METRIC),
    ("taza", "cup", UnitType.VOLUME, "236.588", UnitSystem.US),
    ("cucharada", "tbsp", UnitType.VOLUME, "14.7868", UnitSystem.US),
    ("cucharadita", "tsp", UnitType.VOLUME, "4.92892", UnitSystem.US),
    ("unidad", "u", UnitType.COUNT, "1", UnitSystem.NEUTRAL),
]


def seed_units() -> dict[str, Unit]:
    """The unit catalog keyed by abbreviation."""
    return {
        abbreviation: Unit(UnitId(), name, abbreviation, unit_type, Decimal(factor), system)
        for name, abbreviation, unit_type, factor, system in _SEED_UNITS
    }


def conversion(ingredient: Ingredient, unit: Unit, grams: str) -> IngredientUnitConversion:
    return IngredientUnitConversion(IngredientUnitConversionId(), ingredient.id, unit.id, Decimal(grams))


class InMemoryIngredientRepository(IngredientRepository):

    def __init__(self) -> None:
        self.items: dict[IngredientId, Ingredient] = {}

    async def add(self, ingredient: Ingredient) -> None:
        self.items[ingredient.id] = ingredient

    async def get_by_id(self, ingredient_id):
        return self.items.get(ingredient_id)

    async def get_many_by_ids(self, ids):
        return [self.items[i] for i in ids if i in self.items]

    async def exists_by_name(self, name: str) -> bool:
        # Any language counts, like the real repository.
        return any(name.strip().lower() == text.lower() for i in self.items.values() for text in i.name.all_texts())

    def _matches(self, query, category):
        return sorted(
            (
                i
                for i in self.items.values()
                if (not query or any(query.lower() in text.lower() for text in i.name.all_texts()))
                and (not category or i.default_category == category)
            ),
            key=lambda i: i.name.text.lower(),
        )

    async def search(self, query, category, limit, offset):
        return self._matches(query, category)[offset : offset + limit]

    async def count(self, query, category):
        return len(self._matches(query, category))

    async def list_distinct_categories(self):
        counts: dict[str, int] = {}
        for i in self.items.values():
            if i.default_category is not None:
                counts[i.default_category] = counts.get(i.default_category, 0) + 1
        # Codes are named as written here; the real repository joins ingredient_categories.
        return [(code, LocalizedText.of(code), count) for code, count in sorted(counts.items())]


class InMemoryUnitRepository(UnitRepository):

    def __init__(self, units: dict[str, Unit]) -> None:
        self.units = {unit.id: unit for unit in units.values()}

    async def get_by_id(self, unit_id):
        return self.units.get(unit_id)

    async def get_many_by_ids(self, ids):
        return [self.units[i] for i in ids if i in self.units]

    async def list_all(self):
        return list(self.units.values())


class InMemoryConversionRepository(IngredientUnitConversionRepository):

    def __init__(self) -> None:
        self.items: list[IngredientUnitConversion] = []

    async def add(self, conversion):
        self.items.append(conversion)

    async def get_by_ingredient_and_unit(self, ingredient_id, unit_id):
        return next(
            (c for c in self.items if c.ingredient_id == ingredient_id and c.unit_id == unit_id), None
        )

    async def list_by_ingredients(self, ingredient_ids):
        return [c for c in self.items if c.ingredient_id in ingredient_ids]


class InMemoryUserIngredientRepository(UserIngredientRepository):

    def __init__(self) -> None:
        self.items: list[UserIngredient] = []

    async def add(self, user_ingredient):
        self.items.append(user_ingredient)

    async def update(self, user_ingredient):
        pass  # held by reference

    async def remove(self, user_id, ingredient_id):
        self.items = [i for i in self.items if not (i.user_id == user_id and i.ingredient_id == ingredient_id)]

    async def get_by_user_and_ingredient(self, user_id, ingredient_id):
        return next((i for i in self.items if i.user_id == user_id and i.ingredient_id == ingredient_id), None)

    async def list_by_user(self, user_id):
        return [i for i in self.items if i.user_id == user_id]
