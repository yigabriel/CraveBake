"""
Recipe — aggregate root of the recipes bounded context.

Owns its ingredient lines, equipment, tags, steps and photos: they are only ever changed
through this class, which is where every business rule lives:

- A personalization (`source_recipe_id` set) is always private, never
  modifies the original, and cannot itself be personalized again. The same
  original can be personalized any number of times.
- Max 3 cover photos; max 1 photo per step; a step photo must point to a
  step of this same recipe.
- Steps are numbered 1..n by the aggregate, so `step_number` is unique.
- Ingredient lines and steps may be grouped in named sections ("Masa choux").
  A section exists only while a line uses it, its name is unique per recipe
  (ignoring case), and lines are listed without section first and then each
  section's lines together.
- At most `MAX_TAGS` tags, each listed once.
- Deletion is logical (`deleted_at`): favorites, personalizations and
  preparation sessions may still reference a deleted recipe.

`created_by_user_id` is the opaque id minted by IAM (never IAM's `UserId`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.recipes.domain.entities.recipe_equipment import RecipeEquipment
from app.recipes.domain.entities.recipe_ingredient import RecipeIngredient
from app.recipes.domain.entities.recipe_photo import PhotoType, RecipePhoto, validate_http_url
from app.recipes.domain.entities.recipe_section import (
    MAX_SECTIONS,
    RecipeSection,
    check_grouped,
    clean_section_name,
    section_key,
)
from app.recipes.domain.entities.recipe_step import RecipeStep
from app.recipes.domain.exceptions import (
    CannotPersonalizePersonalizationError,
    CoverPhotoLimitExceededError,
    PersonalizationMustBePrivateError,
    RecipePhotoNotFoundError,
    RecipeStepNotFoundError,
    StepPhotoAlreadyExistsError,
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
from app.shared.exceptions.domain_exceptions import ValidationError

MAX_COVER_PHOTOS = 3
MAX_TITLE_LENGTH = 200
MAX_TAGS = 10


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class _Unset:
    """Sentinel for partial updates: distinguishes "not sent" from an explicit None."""

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _Unset()


@dataclass(frozen=True)
class IngredientLine:
    """Input for `Recipe.replace_ingredients` — an ingredient line without identity yet."""

    ingredient_id: str
    quantity: Decimal
    unit_id: str
    notes: str | None = None
    section: str | None = None  # name of the section it belongs to


@dataclass(frozen=True)
class EquipmentLine:
    """Input for `Recipe.replace_equipment` — an equipment requirement without identity yet."""

    equipment_id: str
    notes: str | None = None


@dataclass(frozen=True)
class StepDraft:
    """Input for `Recipe.replace_steps`. Passing `id` keeps an existing step (and its photo)."""

    instructions: str
    title: str | None = None
    timer_seconds: int | None = None
    id: RecipeStepId | None = None
    section: str | None = None  # name of the section it belongs to


@dataclass
class Recipe:
    id: RecipeId
    created_by_user_id: str
    title: str
    description: str | None = None
    video_url: str | None = None
    category_id: RecipeCategoryId | None = None
    difficulty_id: DifficultyId | None = None
    prep_time_minutes: int | None = None
    servings: int | None = None
    is_public: bool = False
    source_recipe_id: RecipeId | None = None
    ingredients: list[RecipeIngredient] = field(default_factory=list)
    equipment: list[RecipeEquipment] = field(default_factory=list)
    tag_ids: list[RecipeTagId] = field(default_factory=list)
    steps: list[RecipeStep] = field(default_factory=list)
    photos: list[RecipePhoto] = field(default_factory=list)
    sections: list[RecipeSection] = field(default_factory=list)
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    # --- Factories -------------------------------------------------------------

    @classmethod
    def create(
        cls,
        created_by_user_id: str,
        title: str,
        description: str | None = None,
        video_url: str | None = None,
        category_id: RecipeCategoryId | None = None,
        difficulty_id: DifficultyId | None = None,
        prep_time_minutes: int | None = None,
        servings: int | None = None,
        is_public: bool = False,
        ingredients: list[IngredientLine] | None = None,
        steps: list[StepDraft] | None = None,
        equipment: list[EquipmentLine] | None = None,
        tag_ids: list[RecipeTagId] | None = None,
    ) -> "Recipe":
        recipe = cls(id=RecipeId(), created_by_user_id=created_by_user_id, title=_clean_title(title))
        recipe.update_details(
            description=description,
            video_url=video_url,
            category_id=category_id,
            difficulty_id=difficulty_id,
            prep_time_minutes=prep_time_minutes,
            servings=servings,
            is_public=is_public,
        )
        recipe.replace_ingredients(ingredients or [])
        recipe.replace_equipment(equipment or [])
        recipe.replace_tags(tag_ids or [])
        recipe.replace_steps(steps or [])
        return recipe

    def personalize(self, user_id: str, title: str | None = None) -> "Recipe":
        """Creates a private copy owned by `user_id`, linked to this recipe.

        Children are copied with fresh ids; step photos are re-pointed to the
        copied steps. The original is left untouched.
        """
        if self.is_personalization:
            raise CannotPersonalizePersonalizationError()

        section_id_map = {section.id: RecipeSectionId() for section in self.sections}
        step_id_map: dict[RecipeStepId, RecipeStepId] = {}
        copied_steps: list[RecipeStep] = []
        for step in self.steps:
            new_id = RecipeStepId()
            step_id_map[step.id] = new_id
            copied_steps.append(
                RecipeStep(
                    id=new_id,
                    step_number=step.step_number,
                    instructions=step.instructions,
                    title=step.title,
                    timer_seconds=step.timer_seconds,
                    section_id=section_id_map[step.section_id] if step.section_id else None,
                )
            )

        return Recipe(
            id=RecipeId(),
            created_by_user_id=user_id,
            title=_clean_title(title) if title else self.title,
            description=self.description,
            video_url=self.video_url,
            category_id=self.category_id,
            difficulty_id=self.difficulty_id,
            prep_time_minutes=self.prep_time_minutes,
            servings=self.servings,
            is_public=False,
            source_recipe_id=self.id,
            ingredients=[
                RecipeIngredient(
                    id=RecipeIngredientId(),
                    ingredient_id=line.ingredient_id,
                    quantity=line.quantity,
                    unit_id=line.unit_id,
                    notes=line.notes,
                    position=line.position,
                    section_id=section_id_map[line.section_id] if line.section_id else None,
                )
                for line in self.ingredients
            ],
            equipment=[
                RecipeEquipment(id=RecipeEquipmentId(), equipment_id=item.equipment_id, notes=item.notes)
                for item in self.equipment
            ],
            tag_ids=list(self.tag_ids),
            sections=[RecipeSection(id=section_id_map[section.id], name=section.name) for section in self.sections],
            steps=copied_steps,
            photos=[
                RecipePhoto(
                    id=RecipePhotoId(),
                    photo_type=photo.photo_type,
                    photo_url=photo.photo_url,
                    position=photo.position,
                    step_id=step_id_map[photo.step_id] if photo.step_id else None,
                )
                for photo in self.photos
            ],
        )

    # --- Queries ---------------------------------------------------------------

    @property
    def is_personalization(self) -> bool:
        return self.source_recipe_id is not None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def is_owned_by(self, user_id: str) -> bool:
        return self.created_by_user_id == user_id

    def is_visible_to(self, user_id: str) -> bool:
        return not self.is_deleted and (self.is_public or self.is_owned_by(user_id))

    @property
    def distinct_ingredient_count(self) -> int:
        """How many different ingredients the recipe uses (the denominator of ingredient compatibility)."""
        return len({line.ingredient_id for line in self.ingredients})

    @property
    def cover_photos(self) -> list[RecipePhoto]:
        return sorted(
            (photo for photo in self.photos if photo.photo_type == PhotoType.COVER),
            key=lambda photo: photo.position,
        )

    def photo_for_step(self, step_id: RecipeStepId) -> RecipePhoto | None:
        return next((photo for photo in self.photos if photo.step_id == step_id), None)

    # --- Commands --------------------------------------------------------------

    def update_details(
        self,
        title: str | _Unset = UNSET,
        description: str | None | _Unset = UNSET,
        video_url: str | None | _Unset = UNSET,
        category_id: RecipeCategoryId | None | _Unset = UNSET,
        difficulty_id: DifficultyId | None | _Unset = UNSET,
        prep_time_minutes: int | None | _Unset = UNSET,
        servings: int | None | _Unset = UNSET,
        is_public: bool | _Unset = UNSET,
    ) -> None:
        if not isinstance(title, _Unset):
            self.title = _clean_title(title)
        if not isinstance(description, _Unset):
            self.description = (description or "").strip() or None
        if not isinstance(video_url, _Unset):
            self.video_url = validate_http_url(video_url, "Video URL") if video_url else None
        if not isinstance(category_id, _Unset):
            self.category_id = category_id
        if not isinstance(difficulty_id, _Unset):
            self.difficulty_id = difficulty_id
        if not isinstance(prep_time_minutes, _Unset):
            self.prep_time_minutes = _positive_or_none(prep_time_minutes, "Preparation time")
        if not isinstance(servings, _Unset):
            self.servings = _positive_or_none(servings, "Servings")
        if not isinstance(is_public, _Unset):
            if is_public and self.is_personalization:
                raise PersonalizationMustBePrivateError()
            self.is_public = is_public
        self._touch()

    def replace_ingredients(self, lines: list[IngredientLine]) -> None:
        section_ids = self._sections_for([line.section for line in lines])
        self.ingredients = [
            RecipeIngredient(
                id=RecipeIngredientId(),
                ingredient_id=line.ingredient_id,
                quantity=line.quantity,
                unit_id=line.unit_id,
                notes=line.notes,
                position=position,
                section_id=section_id,
            )
            for position, (line, section_id) in enumerate(zip(lines, section_ids), start=1)
        ]
        self._drop_unused_sections()
        self._touch()

    def replace_equipment(self, lines: list[EquipmentLine]) -> None:
        equipment_ids = [line.equipment_id for line in lines]
        if len(set(equipment_ids)) != len(equipment_ids):
            raise ValidationError("The same equipment cannot be listed twice in a recipe")
        self.equipment = [
            RecipeEquipment(id=RecipeEquipmentId(), equipment_id=line.equipment_id, notes=line.notes)
            for line in lines
        ]
        self._touch()

    def replace_tags(self, tag_ids: list[RecipeTagId]) -> None:
        if len(set(tag_ids)) != len(tag_ids):
            raise ValidationError("The same tag cannot be listed twice in a recipe")
        if len(tag_ids) > MAX_TAGS:
            raise ValidationError(f"A recipe cannot have more than {MAX_TAGS} tags")
        self.tag_ids = list(tag_ids)
        self._touch()

    def replace_steps(self, drafts: list[StepDraft]) -> None:
        """Replaces the step list, renumbering 1..n in the given order.

        Drafts carrying the `id` of an existing step keep that identity (and
        its photo); steps left out are removed together with their photo.
        """
        existing_ids = {step.id for step in self.steps}
        kept_ids: set[RecipeStepId] = set()
        new_steps: list[RecipeStep] = []
        section_ids = self._sections_for([draft.section for draft in drafts])

        for number, (draft, section_id) in enumerate(zip(drafts, section_ids), start=1):
            if draft.id is not None:
                if draft.id not in existing_ids:
                    raise RecipeStepNotFoundError(str(draft.id))
                if draft.id in kept_ids:
                    raise ValidationError(f"Step '{draft.id}' appears more than once")
                kept_ids.add(draft.id)
            new_steps.append(
                RecipeStep(
                    id=draft.id or RecipeStepId(),
                    step_number=number,
                    instructions=draft.instructions,
                    title=draft.title,
                    timer_seconds=draft.timer_seconds,
                    section_id=section_id,
                )
            )

        self.steps = new_steps
        self.photos = [
            photo for photo in self.photos if photo.step_id is None or photo.step_id in kept_ids
        ]
        self._drop_unused_sections()
        self._touch()

    def add_cover_photo(self, photo_url: str) -> RecipePhoto:
        covers = self.cover_photos
        if len(covers) >= MAX_COVER_PHOTOS:
            raise CoverPhotoLimitExceededError(MAX_COVER_PHOTOS)
        photo = RecipePhoto(
            id=RecipePhotoId(),
            photo_type=PhotoType.COVER,
            photo_url=photo_url,
            position=(covers[-1].position + 1) if covers else 1,
        )
        self.photos.append(photo)
        self._touch()
        return photo

    def add_step_photo(self, step_id: RecipeStepId, photo_url: str) -> RecipePhoto:
        if not any(step.id == step_id for step in self.steps):
            raise RecipeStepNotFoundError(str(step_id))
        if self.photo_for_step(step_id) is not None:
            raise StepPhotoAlreadyExistsError(str(step_id))
        photo = RecipePhoto(
            id=RecipePhotoId(),
            photo_type=PhotoType.STEP,
            photo_url=photo_url,
            position=1,
            step_id=step_id,
        )
        self.photos.append(photo)
        self._touch()
        return photo

    def remove_photo(self, photo_id: RecipePhotoId) -> None:
        photo = next((photo for photo in self.photos if photo.id == photo_id), None)
        if photo is None:
            raise RecipePhotoNotFoundError(str(photo_id))
        self.photos.remove(photo)
        if photo.photo_type == PhotoType.COVER:
            for position, cover in enumerate(self.cover_photos, start=1):
                cover.position = position
        self._touch()

    def reorder_cover_photos(self, ordered_ids: list[RecipePhotoId]) -> None:
        covers = {photo.id: photo for photo in self.cover_photos}
        if len(ordered_ids) != len(covers) or set(ordered_ids) != set(covers):
            raise ValidationError("The new order must list every cover photo of the recipe exactly once")
        for position, photo_id in enumerate(ordered_ids, start=1):
            covers[photo_id].position = position
        self._touch()

    def soft_delete(self) -> None:
        if self.deleted_at is None:
            self.deleted_at = _utc_now()
            self._touch()

    def _sections_for(self, names: list[str | None]) -> list[RecipeSectionId | None]:
        """The section each line belongs to, creating the ones this recipe does not have yet."""
        cleaned = [clean_section_name(name) for name in names]
        check_grouped(cleaned)
        by_key = {section.key: section for section in self.sections}
        ids: list[RecipeSectionId | None] = []
        for name in cleaned:
            if name is None:
                ids.append(None)
                continue
            section = by_key.get(section_key(name))
            if section is None:
                section = RecipeSection(id=RecipeSectionId(), name=name)
                by_key[section.key] = section
                self.sections.append(section)
            ids.append(section.id)
        return ids

    def _drop_unused_sections(self) -> None:
        used = {line.section_id for line in self.ingredients} | {step.section_id for step in self.steps}
        self.sections = [section for section in self.sections if section.id in used]
        if len(self.sections) > MAX_SECTIONS:
            raise ValidationError(f"A recipe cannot have more than {MAX_SECTIONS} sections")

    def _touch(self) -> None:
        self.updated_at = _utc_now()


def _clean_title(title: str) -> str:
    cleaned = (title or "").strip()
    if not cleaned:
        raise ValidationError("Recipe title cannot be empty")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Recipe title cannot exceed {MAX_TITLE_LENGTH} characters")
    return cleaned


def _positive_or_none(value: int | None, label: str) -> int | None:
    if value is not None and value <= 0:
        raise ValidationError(f"{label} must be greater than zero")
    return value
