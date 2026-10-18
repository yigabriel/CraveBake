from decimal import Decimal

import pytest

from app.recipes.domain.entities.recipe import (
    MAX_TAGS,
    EquipmentLine,
    IngredientLine,
    Recipe,
    StepDraft,
)
from app.recipes.domain.entities.recipe_photo import PhotoType, RecipePhoto
from app.recipes.domain.exceptions import (
    CannotPersonalizePersonalizationError,
    CoverPhotoLimitExceededError,
    PersonalizationMustBePrivateError,
    RecipePhotoNotFoundError,
    RecipeStepNotFoundError,
    StepPhotoAlreadyExistsError,
)
from app.recipes.domain.value_objects.recipe_photo_id import RecipePhotoId
from app.recipes.domain.value_objects.recipe_step_id import RecipeStepId
from app.recipes.domain.value_objects.recipe_tag_id import RecipeTagId
from app.shared.exceptions.domain_exceptions import ValidationError

AUTHOR = "author"
URL = "https://img.example/{}.jpg"


def make_recipe(**overrides) -> Recipe:
    data = dict(
        created_by_user_id=AUTHOR,
        title="Brownies",
        ingredients=[
            IngredientLine("flour", Decimal("2"), "cup"),
            IngredientLine("egg", Decimal("3"), "u", notes="  a temperatura ambiente "),
            IngredientLine("flour", Decimal("1"), "tbsp"),
        ],
        steps=[StepDraft("Mezclar"), StepDraft("Hornear", timer_seconds=1800)],
        equipment=[EquipmentLine("mold")],
        is_public=True,
    )
    data.update(overrides)
    return Recipe.create(**data)


class TestCreate:

    def test_numbers_steps_and_positions(self):
        recipe = make_recipe()
        assert [s.step_number for s in recipe.steps] == [1, 2]
        assert [i.position for i in recipe.ingredients] == [1, 2, 3]
        assert recipe.ingredients[1].notes == "a temperatura ambiente"

    def test_distinct_ingredient_count(self):
        assert make_recipe().distinct_ingredient_count == 2

    @pytest.mark.parametrize("title", ["", "   ", "x" * 201])
    def test_title_rules(self, title):
        with pytest.raises(ValidationError):
            make_recipe(title=title)

    @pytest.mark.parametrize("field", ["prep_time_minutes", "servings"])
    def test_positive_numbers(self, field):
        with pytest.raises(ValidationError):
            make_recipe(**{field: 0})

    def test_video_url_must_be_http(self):
        with pytest.raises(ValidationError):
            make_recipe(video_url="ftp://video")
        assert make_recipe(video_url=" https://youtu.be/x ").video_url == "https://youtu.be/x"

    def test_ingredient_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            make_recipe(ingredients=[IngredientLine("flour", Decimal("0"), "g")])

    def test_step_rules(self):
        with pytest.raises(ValidationError):
            make_recipe(steps=[StepDraft("   ")])
        with pytest.raises(ValidationError):
            make_recipe(steps=[StepDraft("Hornear", timer_seconds=0)])

    def test_duplicate_equipment(self):
        with pytest.raises(ValidationError):
            make_recipe(equipment=[EquipmentLine("mold"), EquipmentLine("mold")])

    def test_tag_rules(self):
        tag = RecipeTagId()
        with pytest.raises(ValidationError):
            make_recipe(tag_ids=[tag, tag])
        with pytest.raises(ValidationError):
            make_recipe(tag_ids=[RecipeTagId() for _ in range(MAX_TAGS + 1)])
        assert len(make_recipe(tag_ids=[RecipeTagId() for _ in range(MAX_TAGS)]).tag_ids) == MAX_TAGS


class TestVisibility:

    def test_public_recipe_visible_to_all(self):
        recipe = make_recipe(is_public=True)
        assert recipe.is_visible_to("anyone")

    def test_private_recipe_only_for_owner(self):
        recipe = make_recipe(is_public=False)
        assert recipe.is_visible_to(AUTHOR)
        assert not recipe.is_visible_to("anyone")

    def test_deleted_recipe_visible_to_nobody(self):
        recipe = make_recipe()
        recipe.soft_delete()
        first_deletion = recipe.deleted_at
        recipe.soft_delete()

        assert recipe.deleted_at == first_deletion
        assert not recipe.is_visible_to(AUTHOR)


class TestUpdateDetails:

    def test_partial_update_leaves_unsent_fields(self):
        recipe = make_recipe(description="Ricos", servings=8)

        recipe.update_details(servings=12)

        assert (recipe.description, recipe.servings) == ("Ricos", 12)

    def test_explicit_none_clears(self):
        recipe = make_recipe(description="Ricos")
        recipe.update_details(description=None)
        assert recipe.description is None


class TestPersonalize:

    def test_creates_private_linked_copy(self):
        original = make_recipe()
        cover = original.add_cover_photo(URL.format("cover"))
        step_photo = original.add_step_photo(original.steps[0].id, URL.format("step"))

        copy = original.personalize("fan", title="Mis brownies")

        assert copy.created_by_user_id == "fan"
        assert copy.title == "Mis brownies"
        assert copy.is_public is False
        assert copy.source_recipe_id == original.id
        assert copy.id != original.id
        assert {s.id for s in copy.steps}.isdisjoint({s.id for s in original.steps})
        copied_step_photo = next(p for p in copy.photos if p.photo_type == PhotoType.STEP)
        assert copied_step_photo.step_id == copy.steps[0].id
        assert copied_step_photo.id != step_photo.id
        assert len(copy.cover_photos) == 1 and copy.cover_photos[0].id != cover.id

    def test_keeps_title_when_not_given(self):
        assert make_recipe().personalize("fan").title == "Brownies"

    def test_original_is_untouched(self):
        original = make_recipe()
        copy = original.personalize("fan")
        copy.replace_steps([StepDraft("Otro")])
        assert [s.instructions for s in original.steps] == ["Mezclar", "Hornear"]

    def test_cannot_personalize_twice(self):
        copy = make_recipe().personalize("fan")
        with pytest.raises(CannotPersonalizePersonalizationError):
            copy.personalize("someone")

    def test_personalization_cannot_be_published(self):
        copy = make_recipe().personalize("fan")
        with pytest.raises(PersonalizationMustBePrivateError):
            copy.update_details(is_public=True)


class TestReplaceSteps:

    def test_keeping_a_step_keeps_its_photo(self):
        recipe = make_recipe()
        first, second = recipe.steps
        recipe.add_step_photo(second.id, URL.format("bake"))

        recipe.replace_steps([StepDraft("Hornear mejor", id=second.id), StepDraft("Servir")])

        assert [(s.step_number, s.instructions) for s in recipe.steps] == [(1, "Hornear mejor"), (2, "Servir")]
        assert recipe.steps[0].id == second.id
        assert recipe.photo_for_step(second.id) is not None

    def test_removed_step_drops_its_photo(self):
        recipe = make_recipe()
        recipe.add_step_photo(recipe.steps[0].id, URL.format("mix"))

        recipe.replace_steps([StepDraft("Nuevo")])

        assert [p for p in recipe.photos if p.photo_type == PhotoType.STEP] == []

    def test_unknown_step_id(self):
        with pytest.raises(RecipeStepNotFoundError):
            make_recipe().replace_steps([StepDraft("x", id=RecipeStepId())])

    def test_same_step_twice(self):
        recipe = make_recipe()
        step_id = recipe.steps[0].id
        with pytest.raises(ValidationError):
            recipe.replace_steps([StepDraft("a", id=step_id), StepDraft("b", id=step_id)])


class TestPhotos:

    def test_cover_limit(self):
        recipe = make_recipe()
        for n in range(3):
            recipe.add_cover_photo(URL.format(n))
        with pytest.raises(CoverPhotoLimitExceededError):
            recipe.add_cover_photo(URL.format(4))

    def test_one_photo_per_step(self):
        recipe = make_recipe()
        recipe.add_step_photo(recipe.steps[0].id, URL.format("a"))
        with pytest.raises(StepPhotoAlreadyExistsError):
            recipe.add_step_photo(recipe.steps[0].id, URL.format("b"))

    def test_step_photo_needs_step_of_this_recipe(self):
        with pytest.raises(RecipeStepNotFoundError):
            make_recipe().add_step_photo(RecipeStepId(), URL.format("a"))

    def test_remove_cover_renumbers(self):
        recipe = make_recipe()
        a, b, c = (recipe.add_cover_photo(URL.format(n)) for n in "abc")

        recipe.remove_photo(a.id)

        assert [(p.id, p.position) for p in recipe.cover_photos] == [(b.id, 1), (c.id, 2)]

    def test_remove_unknown_photo(self):
        with pytest.raises(RecipePhotoNotFoundError):
            make_recipe().remove_photo(RecipePhotoId())

    def test_reorder_covers(self):
        recipe = make_recipe()
        a, b, c = (recipe.add_cover_photo(URL.format(n)) for n in "abc")

        recipe.reorder_cover_photos([c.id, a.id, b.id])

        assert [p.id for p in recipe.cover_photos] == [c.id, a.id, b.id]

    @pytest.mark.parametrize("pick", [lambda a, b: [a], lambda a, b: [a, a], lambda a, b: [a, RecipePhotoId()]])
    def test_reorder_must_list_every_cover_once(self, pick):
        recipe = make_recipe()
        a, b = (recipe.add_cover_photo(URL.format(n)) for n in "ab")
        with pytest.raises(ValidationError):
            recipe.reorder_cover_photos(pick(a.id, b.id))

    @pytest.mark.parametrize("url", ["", "notaurl", "https://", "javascript:alert(1)"])
    def test_photo_url_must_be_http(self, url):
        with pytest.raises(ValidationError):
            RecipePhoto(RecipePhotoId(), PhotoType.COVER, url)

    def test_photo_type_and_step_must_agree(self):
        with pytest.raises(ValidationError):
            RecipePhoto(RecipePhotoId(), PhotoType.STEP, URL.format("x"))
        with pytest.raises(ValidationError):
            RecipePhoto(RecipePhotoId(), PhotoType.COVER, URL.format("x"), step_id=RecipeStepId())
