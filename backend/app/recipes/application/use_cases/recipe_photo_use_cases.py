"""
Photo use cases of a recipe (owner only): add, remove and reorder covers.

Photos are registered by URL (there is no file upload yet). The limits
(max 3 covers, max 1 photo per step) are enforced by the `Recipe` aggregate.
"""
from __future__ import annotations

from app.recipes.application.dto.recipe_dto import AddRecipePhotoDTO, RecipePhotoDTO
from app.recipes.application.mappers.recipe_assembler import photo_to_dto
from app.recipes.application.services.recipe_access import load_owned_recipe, load_visible_recipe
from app.recipes.domain.entities.recipe_photo import PhotoType
from app.recipes.domain.exceptions import RecipePhotoNotFoundError, RecipeStepNotFoundError
from app.recipes.domain.repositories.recipe_repository import RecipeRepository
from app.recipes.domain.value_objects.recipe_photo_id import RecipePhotoId
from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId
from app.shared.exceptions.domain_exceptions import ValidationError


class ListRecipePhotosUseCase:
    def __init__(self, recipe_repository: RecipeRepository) -> None:
        self._recipe_repository = recipe_repository

    async def execute(self, user_id: str, recipe_id: str) -> list[RecipePhotoDTO]:
        recipe = await load_visible_recipe(self._recipe_repository, recipe_id, user_id)
        step_numbers = {step.id: step.step_number for step in recipe.steps}
        step_photos = sorted(
            (photo for photo in recipe.photos if photo.photo_type == PhotoType.STEP),
            key=lambda photo: step_numbers.get(photo.step_id, 0),
        )
        return [photo_to_dto(photo) for photo in [*recipe.cover_photos, *step_photos]]


class AddRecipePhotoUseCase:
    def __init__(self, recipe_repository: RecipeRepository) -> None:
        self._recipe_repository = recipe_repository

    async def execute(self, dto: AddRecipePhotoDTO) -> RecipePhotoDTO:
        recipe = await load_owned_recipe(self._recipe_repository, dto.recipe_id, dto.user_id)

        if dto.photo_type == PhotoType.COVER.value:
            if dto.step_id is not None:
                raise ValidationError("A cover photo cannot reference a step")
            photo = recipe.add_cover_photo(dto.photo_url)
        elif dto.photo_type == PhotoType.STEP.value:
            if dto.step_id is None:
                raise ValidationError("A step photo must include 'step_id'")
            step_id = RecipeStepId.try_from_string(dto.step_id)
            if step_id is None:
                raise RecipeStepNotFoundError(dto.step_id)
            photo = recipe.add_step_photo(step_id, dto.photo_url)
        else:
            raise ValidationError("photo_type must be 'cover' or 'step'")

        await self._recipe_repository.update(recipe)
        return photo_to_dto(photo)


class RemoveRecipePhotoUseCase:
    def __init__(self, recipe_repository: RecipeRepository) -> None:
        self._recipe_repository = recipe_repository

    async def execute(self, user_id: str, recipe_id: str, photo_id: str) -> None:
        recipe = await load_owned_recipe(self._recipe_repository, recipe_id, user_id)
        parsed_id = RecipePhotoId.try_from_string(photo_id)
        if parsed_id is None:
            raise RecipePhotoNotFoundError(photo_id)
        recipe.remove_photo(parsed_id)
        await self._recipe_repository.update(recipe)


class ReorderCoverPhotosUseCase:
    def __init__(self, recipe_repository: RecipeRepository) -> None:
        self._recipe_repository = recipe_repository

    async def execute(self, user_id: str, recipe_id: str, photo_ids: list[str]) -> list[RecipePhotoDTO]:
        recipe = await load_owned_recipe(self._recipe_repository, recipe_id, user_id)
        parsed_ids = []
        for raw in photo_ids:
            parsed = RecipePhotoId.try_from_string(raw)
            if parsed is None:
                raise RecipePhotoNotFoundError(raw)
            parsed_ids.append(parsed)
        recipe.reorder_cover_photos(parsed_ids)
        await self._recipe_repository.update(recipe)
        return [photo_to_dto(photo) for photo in recipe.cover_photos]
