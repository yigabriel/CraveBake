"""In-memory test doubles for the recipes ports, plus a ready-made wiring of the use case collaborators."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.recipes.application.mappers.recipe_assembler import RecipeAssembler
from app.recipes.application.services.recipe_reference_validator import RecipeReferenceValidator
from app.recipes.domain.entities.difficulty import Difficulty
from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.entities.recipe_category import RecipeCategory
from app.recipes.domain.entities.recipe_tag import RecipeTag, TagGroup
from app.recipes.domain.repositories.recipe_catalog_repositories import (
    DifficultyRepository,
    RecipeCategoryRepository,
    RecipeTagRepository,
)
from app.recipes.domain.repositories.recipe_repository import (
    RankedRecipeIds,
    RecipePage,
    RecipeRepository,
)
from app.recipes.domain.services.equipment_catalog import CatalogEquipment, EquipmentCatalog
from app.recipes.domain.services.ingredient_catalog import CatalogIngredient, CatalogUnit, IngredientCatalog
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId


class InMemoryRecipeRepository(RecipeRepository):

    def __init__(self) -> None:
        self.items: dict = {}
        self.last_search = None
        self.last_overlap_query = None

    async def add(self, recipe):
        self.items[recipe.id] = recipe

    async def update(self, recipe):
        self.items[recipe.id] = recipe

    async def get_by_id(self, recipe_id):
        return self.items.get(recipe_id)

    async def get_many_by_ids(self, recipe_ids):
        return [self.items[i] for i in recipe_ids if i in self.items]

    async def rank_by_ingredient_overlap(self, query):
        self.last_overlap_query = query
        return RankedRecipeIds(recipe_ids=[], total=0)

    async def search_public(self, criteria):
        self.last_search = criteria
        matches = [
            r
            for r in self.items.values()
            if r.is_public
            and not r.is_deleted
            and (not criteria.query or criteria.query.lower() in r.title.lower())
            and {i.ingredient_id for i in r.ingredients}.issuperset(criteria.ingredient_ids)
        ]
        return RecipePage(items=matches[criteria.offset : criteria.offset + criteria.limit], total=len(matches))

    def _owned(self, user_id):
        return sorted(
            (r for r in self.items.values() if r.created_by_user_id == user_id and not r.is_deleted),
            key=lambda r: r.created_at,
            reverse=True,
        )

    async def list_by_owner(self, user_id, personalized=None, limit=None, offset=0):
        matches = [r for r in self._owned(user_id) if personalized is None or r.is_personalization == personalized]
        end = None if limit is None else offset + limit
        return RecipePage(items=matches[offset:end], total=len(matches))

    async def list_personalizations(self, source_recipe_id, user_id, limit=None, offset=0):
        matches = [r for r in self._owned(user_id) if r.source_recipe_id == source_recipe_id]
        end = None if limit is None else offset + limit
        return RecipePage(items=matches[offset:end], total=len(matches))


class _ListRepo:
    def __init__(self, *items) -> None:
        self.items = {item.id: item for item in items}

    async def get_by_id(self, item_id):
        return self.items.get(item_id)

    async def get_many_by_ids(self, ids):
        return [self.items[i] for i in ids if i in self.items]

    async def list_all(self):
        return list(self.items.values())


class FakeCategoryRepository(_ListRepo, RecipeCategoryRepository):
    pass


class FakeDifficultyRepository(_ListRepo, DifficultyRepository):
    pass


class FakeTagRepository(_ListRepo, RecipeTagRepository):
    pass


class FakeIngredientCatalog(IngredientCatalog):

    def __init__(self, ingredients: dict[str, str], units: dict[str, str]) -> None:
        self.ingredients = ingredients
        self.units = units

    async def get_ingredients(self, ids):
        return {i: CatalogIngredient(i, self.ingredients[i]) for i in ids if i in self.ingredients}

    async def get_units(self, ids):
        return {u: CatalogUnit(u, self.units[u], self.units[u]) for u in ids if u in self.units}


class FakeEquipmentCatalog(EquipmentCatalog):

    def __init__(self, equipment: dict[str, str]) -> None:
        self.equipment = equipment

    async def get_equipment(self, ids):
        return {e: CatalogEquipment(e, self.equipment[e]) for e in ids if e in self.equipment}


def _id() -> str:
    return str(uuid.uuid4())


@dataclass
class RecipesWorld:
    """Every collaborator the recipe use cases need, wired with a small seeded catalog."""

    flour: str = field(default_factory=_id)
    egg: str = field(default_factory=_id)
    grams: str = field(default_factory=_id)
    units: str = field(default_factory=_id)
    mold: str = field(default_factory=_id)
    cakes: RecipeCategory = field(default_factory=lambda: RecipeCategory(RecipeCategoryId(), "Tortas"))
    easy: Difficulty = field(default_factory=lambda: Difficulty(DifficultyId(), "Fácil", 1))
    chocolate: RecipeTag = field(default_factory=lambda: RecipeTag(RecipeTagId(), "chocolate", TagGroup.SABOR))
    vegan: RecipeTag = field(default_factory=lambda: RecipeTag(RecipeTagId(), "vegano", TagGroup.DIETA))
    holiday: RecipeTag = field(default_factory=lambda: RecipeTag(RecipeTagId(), "Navidad", TagGroup.CELEBRACIONES))

    def __post_init__(self) -> None:
        self.recipes = InMemoryRecipeRepository()
        self.categories = FakeCategoryRepository(self.cakes)
        self.difficulties = FakeDifficultyRepository(self.easy)
        self.tags = FakeTagRepository(self.holiday, self.vegan, self.chocolate)
        self.ingredient_catalog = FakeIngredientCatalog(
            {self.flour: "Harina", self.egg: "Huevo"}, {self.grams: "g", self.units: "u"}
        )
        self.equipment_catalog = FakeEquipmentCatalog({self.mold: "Molde"})
        self.validator = RecipeReferenceValidator(
            self.categories, self.difficulties, self.ingredient_catalog, self.equipment_catalog, self.tags
        )
        self.assembler = RecipeAssembler(
            self.recipes, self.categories, self.difficulties, self.ingredient_catalog, self.equipment_catalog, self.tags
        )

    async def store(self, recipe: Recipe) -> Recipe:
        await self.recipes.add(recipe)
        return recipe
