"""
SQLAlchemy implementation of `RecipeRepository`.

The aggregate spans seven tables (recipes, recipe_sections, recipe_steps, recipe_ingredients,
recipe_equipment, recipe_tags, recipe_photos). Saving synchronizes the child rows by id instead of
delete-and-reinsert, so a step keeps its id (and anything pointing to it,
like its photo or a preparation session's current step) across edits.

Child writes are flushed in dependency order (photos removed before steps,
sections written before the lines that reference them and removed after them,
steps inserted before the photos that reference them), so no ORM
relationships are needed to get the statement order right.

`rank_by_ingredient_overlap` scores, filters, orders and paginates in one
SQL statement, so ranking cost does not grow with what the user is shown:
only the requested page of ids leaves the database.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import Float, cast, distinct, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.shared.database.text_search import contains_folded
from app.shared.domain.value_objects.entity_id import EntityId

from app.recipes.domain.entities.recipe import Recipe
from app.recipes.domain.entities.recipe_equipment import RecipeEquipment
from app.recipes.domain.entities.recipe_ingredient import RecipeIngredient
from app.recipes.domain.entities.recipe_photo import PhotoType, RecipePhoto
from app.recipes.domain.entities.recipe_section import RecipeSection
from app.recipes.domain.entities.recipe_step import RecipeStep
from app.recipes.domain.repositories.recipe_repository import (
    IngredientOverlapQuery,
    RankedRecipeIds,
    RecipePage,
    RecipeRepository,
    RecipeSearchCriteria,
)
from app.recipes.domain.value_objects.difficulty_id import DifficultyId
from app.recipes.domain.value_objects.recipe_category_id import RecipeCategoryId
from app.recipes.domain.value_objects.recipe_equipment_id import RecipeEquipmentId
from app.recipes.domain.value_objects.recipe_id import RecipeId
from app.recipes.domain.value_objects.recipe_ingredient_id import RecipeIngredientId
from app.recipes.domain.value_objects.recipe_photo_id import RecipePhotoId
from app.recipes.domain.value_objects.recipe_section_id import RecipeSectionId
from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.recipes.infraestructure.persistence.models.recipe_equipment_model import RecipeEquipmentModel
from app.recipes.infraestructure.persistence.models.recipe_ingredient_model import RecipeIngredientModel
from app.recipes.infraestructure.persistence.models.recipe_model import RecipeModel
from app.recipes.infraestructure.persistence.models.recipe_photo_model import RecipePhotoModel
from app.recipes.infraestructure.persistence.models.recipe_section_model import RecipeSectionModel
from app.recipes.infraestructure.persistence.models.recipe_step_model import RecipeStepModel
from app.recipes.infraestructure.persistence.models.tag_models import RecipeTagModel


class SqlAlchemyRecipeRepository(RecipeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Writes ------------------------------------------------------------------

    async def add(self, recipe: Recipe) -> None:
        model = RecipeModel(
            id=recipe.id.value,
            created_by_user_id=uuid.UUID(recipe.created_by_user_id),
            created_at=recipe.created_at,
        )
        _copy_recipe_fields(recipe, model)
        self._session.add(model)
        await self._session.flush()
        await self._sync_children(recipe)

    async def update(self, recipe: Recipe) -> None:
        model = await self._session.get(RecipeModel, recipe.id.value)
        if model is None:
            return
        _copy_recipe_fields(recipe, model)
        await self._session.flush()
        await self._sync_children(recipe)

    async def _sync_children(self, recipe: Recipe) -> None:
        recipe_uuid = recipe.id.value
        existing_sections = await self._existing(RecipeSectionModel, recipe_uuid)
        existing_steps = await self._existing(RecipeStepModel, recipe_uuid)
        existing_ingredients = await self._existing(RecipeIngredientModel, recipe_uuid)
        existing_equipment = await self._existing(RecipeEquipmentModel, recipe_uuid)
        existing_photos = await self._existing(RecipePhotoModel, recipe_uuid)

        desired_sections = {section.id.value: {"name": section.name} for section in recipe.sections}
        desired_steps = {step.id.value: _step_values(step) for step in recipe.steps}
        desired_ingredients = {line.id.value: _ingredient_values(line) for line in recipe.ingredients}
        desired_equipment = {item.id.value: _equipment_values(item) for item in recipe.equipment}
        desired_photos = {photo.id.value: _photo_values(photo) for photo in recipe.photos}

        # 1) removals, children-of-children first
        await self._delete_missing(existing_photos, desired_photos)
        await self._delete_missing(existing_ingredients, desired_ingredients)
        await self._delete_missing(existing_equipment, desired_equipment)
        await self._delete_missing(existing_steps, desired_steps)
        # 2) inserts/updates, referenced rows first
        await self._upsert(RecipeSectionModel, recipe_uuid, existing_sections, desired_sections)
        await self._upsert(RecipeStepModel, recipe_uuid, existing_steps, desired_steps)
        await self._upsert(RecipeIngredientModel, recipe_uuid, existing_ingredients, desired_ingredients)
        await self._upsert(RecipeEquipmentModel, recipe_uuid, existing_equipment, desired_equipment)
        await self._upsert(RecipePhotoModel, recipe_uuid, existing_photos, desired_photos)
        # 3) sections no line points to any more (the lines were already moved off them)
        await self._delete_missing(existing_sections, desired_sections)
        await self._sync_tags(recipe)

    async def _sync_tags(self, recipe: Recipe) -> None:
        # Tag links have no identity of their own in the domain: sync them by tag id.
        existing = await self._existing(RecipeTagModel, recipe.id.value)
        desired = {tag_id.value for tag_id in recipe.tag_ids}
        for model in existing.values():
            if model.tag_id not in desired:
                await self._session.delete(model)
        await self._session.flush()
        present = {model.tag_id for model in existing.values()}
        for tag_uuid in desired - present:
            self._session.add(RecipeTagModel(id=uuid.uuid4(), recipe_id=recipe.id.value, tag_id=tag_uuid))
        await self._session.flush()

    async def _existing(self, model_cls: type, recipe_uuid: uuid.UUID) -> dict[uuid.UUID, Any]:
        result = await self._session.execute(select(model_cls).where(model_cls.recipe_id == recipe_uuid))
        return {model.id: model for model in result.scalars().all()}

    async def _delete_missing(self, existing: dict[uuid.UUID, Any], desired: dict[uuid.UUID, dict]) -> None:
        for model_id, model in existing.items():
            if model_id not in desired:
                await self._session.delete(model)
        await self._session.flush()

    async def _upsert(
        self,
        model_cls: type,
        recipe_uuid: uuid.UUID,
        existing: dict[uuid.UUID, Any],
        desired: dict[uuid.UUID, dict],
    ) -> None:
        for model_id, values in desired.items():
            model = existing.get(model_id)
            if model is None:
                self._session.add(model_cls(id=model_id, recipe_id=recipe_uuid, **values))
                continue
            for column, value in values.items():
                if getattr(model, column) != value:
                    setattr(model, column, value)
        await self._session.flush()

    # --- Reads -------------------------------------------------------------------

    async def get_by_id(self, recipe_id: RecipeId) -> Recipe | None:
        model = await self._session.get(RecipeModel, recipe_id.value)
        if model is None:
            return None
        return (await self._to_entities([model]))[0]

    async def get_many_by_ids(self, recipe_ids: list[RecipeId]) -> list[Recipe]:
        if not recipe_ids:
            return []
        result = await self._session.execute(
            select(RecipeModel).where(RecipeModel.id.in_({recipe_id.value for recipe_id in recipe_ids}))
        )
        return await self._to_entities(list(result.scalars().all()))

    async def rank_by_ingredient_overlap(self, query: IngredientOverlapQuery) -> RankedRecipeIds:
        ingredient_uuids = _uuids(query.ingredient_ids)
        if not ingredient_uuids:
            return RankedRecipeIds(recipe_ids=[], total=0)
        viewer = uuid.UUID(query.viewer_user_id)

        # Start from the viewer's ingredients (index on ingredient_id), not from every recipe.
        matched = (
            select(
                RecipeIngredientModel.recipe_id.label("recipe_id"),
                func.count(distinct(RecipeIngredientModel.ingredient_id)).label("matched"),
            )
            .where(RecipeIngredientModel.ingredient_id.in_(ingredient_uuids))
            .group_by(RecipeIngredientModel.recipe_id)
            .cte("matched")
        )
        equipment = (
            select(
                RecipeEquipmentModel.recipe_id.label("recipe_id"),
                func.count().label("total"),
                func.count()
                .filter(RecipeEquipmentModel.equipment_id.in_(_uuids(query.equipment_ids)))
                .label("owned"),
            )
            .where(RecipeEquipmentModel.recipe_id.in_(select(matched.c.recipe_id)))
            .group_by(RecipeEquipmentModel.recipe_id)
            .cte("equipment")
        )
        ingredient_score = cast(matched.c.matched, Float) / RecipeModel.ingredient_count
        equipment_score = func.coalesce(cast(equipment.c.owned, Float) / func.nullif(equipment.c.total, 0), 1.0)
        rank_score = query.ingredient_weight * ingredient_score + query.equipment_weight * equipment_score
        personalization = aliased(RecipeModel)

        conditions = [
            RecipeModel.deleted_at.is_(None),
            or_(RecipeModel.is_public.is_(True), RecipeModel.created_by_user_id == viewer),
            RecipeModel.ingredient_count > 0,
            ingredient_score >= query.min_ingredient_score,
            # The viewer's own version replaces the original they personalized.
            ~exists().where(
                personalization.source_recipe_id == RecipeModel.id,
                personalization.created_by_user_id == viewer,
                personalization.deleted_at.is_(None),
            ),
        ]
        if query.excluded_recipe_ids:
            conditions.append(RecipeModel.id.not_in([recipe_id.value for recipe_id in query.excluded_recipe_ids]))
        if query.category_id:
            conditions.append(RecipeModel.category_id == query.category_id.value)
        conditions.extend(_has_all_tags(query.tag_ids))

        statement = (
            select(RecipeModel.id, func.count().over().label("total"))
            .select_from(matched)
            .join(RecipeModel, RecipeModel.id == matched.c.recipe_id)
            .outerjoin(equipment, equipment.c.recipe_id == RecipeModel.id)
            .where(*conditions)
            .order_by(
                rank_score.desc(),
                ingredient_score.desc(),
                (RecipeModel.ingredient_count - matched.c.matched).asc(),
                func.lower(RecipeModel.title),
                RecipeModel.id,
            )
            .limit(query.limit)
            .offset(query.offset)
        )
        rows = (await self._session.execute(statement)).all()
        if rows:
            total = rows[0].total
        elif query.offset == 0:
            total = 0
        else:  # page past the end: the window function had no row to report the total on
            count_statement = (
                select(func.count())
                .select_from(matched)
                .join(RecipeModel, RecipeModel.id == matched.c.recipe_id)
                .outerjoin(equipment, equipment.c.recipe_id == RecipeModel.id)
                .where(*conditions)
            )
            total = (await self._session.execute(count_statement)).scalar_one()
        return RankedRecipeIds(recipe_ids=[RecipeId(row.id) for row in rows], total=total)

    async def search_public(self, criteria: RecipeSearchCriteria) -> RecipePage:
        conditions = [RecipeModel.is_public.is_(True), RecipeModel.deleted_at.is_(None)]
        if criteria.query:
            conditions.append(
                or_(contains_folded(RecipeModel.title, criteria.query), contains_folded(RecipeModel.description, criteria.query))
            )
        if criteria.category_id:
            conditions.append(RecipeModel.category_id == criteria.category_id.value)
        if criteria.difficulty_id:
            conditions.append(RecipeModel.difficulty_id == criteria.difficulty_id.value)
        if criteria.max_prep_time_minutes is not None:
            conditions.append(RecipeModel.prep_time_minutes <= criteria.max_prep_time_minutes)
        for ingredient_id in criteria.ingredient_ids:
            conditions.append(
                exists().where(
                    RecipeIngredientModel.recipe_id == RecipeModel.id,
                    RecipeIngredientModel.ingredient_id == uuid.UUID(ingredient_id),
                )
            )
        conditions.extend(_has_all_tags(criteria.tag_ids))
        return await self._page(conditions, criteria.limit, criteria.offset)

    async def list_by_owner(
        self,
        user_id: str,
        personalized: bool | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> RecipePage:
        conditions = [RecipeModel.created_by_user_id == uuid.UUID(user_id), RecipeModel.deleted_at.is_(None)]
        if personalized is True:
            conditions.append(RecipeModel.source_recipe_id.is_not(None))
        elif personalized is False:
            conditions.append(RecipeModel.source_recipe_id.is_(None))
        return await self._page(conditions, limit, offset)

    async def list_personalizations(
        self, source_recipe_id: RecipeId, user_id: str, limit: int | None = None, offset: int = 0
    ) -> RecipePage:
        conditions = [
            RecipeModel.source_recipe_id == source_recipe_id.value,
            RecipeModel.created_by_user_id == uuid.UUID(user_id),
            RecipeModel.deleted_at.is_(None),
        ]
        return await self._page(conditions, limit, offset)

    async def _page(self, conditions: list, limit: int | None, offset: int) -> RecipePage:
        """Newest first, with the total count of matches before pagination."""
        total = (
            await self._session.execute(select(func.count()).select_from(RecipeModel).where(*conditions))
        ).scalar_one()
        statement = (
            select(RecipeModel).where(*conditions).order_by(RecipeModel.created_at.desc(), RecipeModel.id)
        )
        if limit is not None:
            statement = statement.limit(limit)
        if offset:
            statement = statement.offset(offset)
        result = await self._session.execute(statement)
        return RecipePage(items=await self._to_entities(list(result.scalars().all())), total=total)

    async def _to_entities(self, models: list[RecipeModel]) -> list[Recipe]:
        """Loads the children of all given recipes with one query per child table."""
        if not models:
            return []
        ids = [model.id for model in models]
        sections = await self._children_by_recipe(RecipeSectionModel, ids)
        steps = await self._children_by_recipe(RecipeStepModel, ids)
        ingredients = await self._children_by_recipe(RecipeIngredientModel, ids)
        equipment = await self._children_by_recipe(RecipeEquipmentModel, ids)
        tags = await self._children_by_recipe(RecipeTagModel, ids)
        photos = await self._children_by_recipe(RecipePhotoModel, ids)
        return [
            _to_entity(
                model,
                sections[model.id],
                steps[model.id],
                ingredients[model.id],
                equipment[model.id],
                tags[model.id],
                photos[model.id],
            )
            for model in models
        ]

    async def _children_by_recipe(self, model_cls: type, recipe_ids: list[uuid.UUID]) -> dict[uuid.UUID, list]:
        result = await self._session.execute(select(model_cls).where(model_cls.recipe_id.in_(recipe_ids)))
        grouped: dict[uuid.UUID, list] = defaultdict(list)
        for child in result.scalars().all():
            grouped[child.recipe_id].append(child)
        return grouped


# --- Query helpers -----------------------------------------------------------------


def _uuids(raw_ids: list[str]) -> list[uuid.UUID]:
    return list({parsed.value for raw in raw_ids if (parsed := EntityId.try_from_string(raw)) is not None})


def _has_all_tags(tag_ids: list[RecipeTagId]) -> list:
    return [
        exists().where(RecipeTagModel.recipe_id == RecipeModel.id, RecipeTagModel.tag_id == tag_id.value)
        for tag_id in tag_ids
    ]


# --- Mapping helpers ---------------------------------------------------------------


def _copy_recipe_fields(recipe: Recipe, model: RecipeModel) -> None:
    model.source_recipe_id = recipe.source_recipe_id.value if recipe.source_recipe_id else None
    model.title = recipe.title
    model.description = recipe.description
    model.video_url = recipe.video_url
    model.category_id = recipe.category_id.value if recipe.category_id else None
    model.difficulty_id = recipe.difficulty_id.value if recipe.difficulty_id else None
    model.prep_time_minutes = recipe.prep_time_minutes
    model.servings = recipe.servings
    model.is_public = recipe.is_public
    model.ingredient_count = recipe.distinct_ingredient_count
    model.deleted_at = recipe.deleted_at
    # Explicit, not `onupdate`: editing only children (steps, photos) never
    # touches the recipe row, yet it is still a change to the recipe.
    model.updated_at = recipe.updated_at


def _step_values(step: RecipeStep) -> dict[str, Any]:
    return {
        "step_number": step.step_number,
        "title": step.title,
        "instructions": step.instructions,
        "timer_seconds": step.timer_seconds,
        "section_id": step.section_id.value if step.section_id else None,
    }


def _ingredient_values(line: RecipeIngredient) -> dict[str, Any]:
    return {
        "ingredient_id": uuid.UUID(line.ingredient_id),
        "quantity": line.quantity,
        "unit_id": uuid.UUID(line.unit_id),
        "notes": line.notes,
        "position": line.position,
        "section_id": line.section_id.value if line.section_id else None,
    }


def _equipment_values(item: RecipeEquipment) -> dict[str, Any]:
    return {"equipment_id": uuid.UUID(item.equipment_id), "notes": item.notes}


def _photo_values(photo: RecipePhoto) -> dict[str, Any]:
    return {
        "photo_type": photo.photo_type.value,
        "step_id": photo.step_id.value if photo.step_id else None,
        "photo_url": photo.photo_url,
        "position": photo.position,
    }


def _to_entity(
    model: RecipeModel,
    sections: list[RecipeSectionModel],
    steps: list[RecipeStepModel],
    ingredients: list[RecipeIngredientModel],
    equipment: list[RecipeEquipmentModel],
    tags: list[RecipeTagModel],
    photos: list[RecipePhotoModel],
) -> Recipe:
    return Recipe(
        id=RecipeId(model.id),
        created_by_user_id=str(model.created_by_user_id),
        title=model.title,
        description=model.description,
        video_url=model.video_url,
        category_id=RecipeCategoryId(model.category_id) if model.category_id else None,
        difficulty_id=DifficultyId(model.difficulty_id) if model.difficulty_id else None,
        prep_time_minutes=model.prep_time_minutes,
        servings=model.servings,
        is_public=model.is_public,
        source_recipe_id=RecipeId(model.source_recipe_id) if model.source_recipe_id else None,
        steps=[
            RecipeStep(
                id=RecipeStepId(step.id),
                step_number=step.step_number,
                instructions=step.instructions,
                title=step.title,
                timer_seconds=step.timer_seconds,
                section_id=RecipeSectionId(step.section_id) if step.section_id else None,
            )
            for step in sorted(steps, key=lambda step: step.step_number)
        ],
        ingredients=[
            RecipeIngredient(
                id=RecipeIngredientId(line.id),
                ingredient_id=str(line.ingredient_id),
                quantity=line.quantity,
                unit_id=str(line.unit_id),
                notes=line.notes,
                position=line.position,
                section_id=RecipeSectionId(line.section_id) if line.section_id else None,
            )
            for line in sorted(ingredients, key=lambda line: line.position)
        ],
        equipment=[
            RecipeEquipment(id=RecipeEquipmentId(item.id), equipment_id=str(item.equipment_id), notes=item.notes)
            for item in sorted(equipment, key=lambda item: (item.created_at, item.id))
        ],
        tag_ids=[RecipeTagId(link.tag_id) for link in sorted(tags, key=lambda link: (link.created_at, link.id))],
        photos=[
            RecipePhoto(
                id=RecipePhotoId(photo.id),
                photo_type=PhotoType(photo.photo_type),
                photo_url=photo.photo_url,
                position=photo.position,
                step_id=RecipeStepId(photo.step_id) if photo.step_id else None,
                created_at=photo.created_at,
            )
            for photo in photos
        ],
        sections=[
            RecipeSection(id=RecipeSectionId(section.id), name=section.name)
            for section in sorted(sections, key=lambda section: (section.created_at, section.id))
        ],
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
