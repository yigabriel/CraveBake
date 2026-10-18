"""
Anti-corruption layer: implements preparation's ports on top of the public
APIs of recipes (`RecipeQueryService`) and ingredients
(`IngredientQueryService`), translating their DTOs into this module's types.
"""
from __future__ import annotations

from app.ingredients.application.dto.display_quantity_dto import QuantityToDisplayDTO
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.preparation.domain.services.ports import (
    IngredientToPrepare,
    QuantityDisplay,
    QuantityToShow,
    RecipeSource,
    RecipeToPrepare,
    ShownQuantity,
    StepToPrepare,
)
from app.recipes.application.public.recipe_query_service import RecipeQueryService


class RecipesModuleSource(RecipeSource):
    def __init__(self, recipes: RecipeQueryService) -> None:
        self._recipes = recipes

    async def get_recipe_to_prepare(self, recipe_id: str, viewer_user_id: str) -> RecipeToPrepare | None:
        detail = await self._recipes.get_detail(recipe_id, viewer_user_id)
        if detail is None:
            return None
        return RecipeToPrepare(
            id=detail.id,
            title=detail.title,
            cover_photo_url=detail.cover_photos[0].photo_url if detail.cover_photos else None,
            servings=detail.servings,
            ingredients=[
                IngredientToPrepare(
                    ingredient_id=line.ingredient_id,
                    ingredient_name=line.ingredient_name,
                    quantity=line.quantity,
                    unit_id=line.unit_id,
                    unit_abbreviation=line.unit_abbreviation,
                    notes=line.notes,
                    position=line.position,
                )
                for line in detail.ingredients
            ],
            steps=[
                StepToPrepare(
                    source_step_id=step.id,
                    step_number=step.step_number,
                    instructions=step.instructions,
                    title=step.title,
                    timer_seconds=step.timer_seconds,
                    photo_url=step.photo.photo_url if step.photo else None,
                )
                for step in detail.steps
            ],
        )


class IngredientsQuantityDisplay(QuantityDisplay):
    def __init__(self, ingredients: IngredientQueryService) -> None:
        self._ingredients = ingredients

    async def show_in(self, quantities: list[QuantityToShow], unit_system: str) -> list[ShownQuantity]:
        shown = await self._ingredients.display_in_unit_system(
            [QuantityToDisplayDTO(item.ingredient_id, item.quantity, item.unit_id) for item in quantities],
            unit_system,
        )
        return [ShownQuantity(item.quantity, item.unit_abbreviation, item.converted) for item in shown]
