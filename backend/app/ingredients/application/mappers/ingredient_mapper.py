"""Maps the Ingredient domain entity to IngredientDTO."""
from app.ingredients.application.dto.ingredient_dto import IngredientDTO
from app.ingredients.domain.entities.ingredient import Ingredient


def ingredient_to_dto(ingredient: Ingredient) -> IngredientDTO:
    return IngredientDTO(
        id=str(ingredient.id),
        name=ingredient.name,
        description=ingredient.description,
        default_category=ingredient.default_category,
    )
