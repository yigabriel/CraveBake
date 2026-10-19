from datetime import timedelta
from decimal import Decimal

import pytest

from app.recipes.application.dto.recipe_dto import (
    AddRecipePhotoDTO,
    CreateRecipeDTO,
    IngredientOverlapQueryDTO,
    RecipeEquipmentInputDTO,
    RecipeIngredientInputDTO,
    RecipeStepInputDTO,
    SearchRecipesDTO,
    UpdateRecipeDTO,
)
from app.recipes.application.public.recipe_query_service import RecipeQueryService
from app.recipes.application.use_cases.create_recipe_use_case import CreateRecipeUseCase
from app.recipes.application.use_cases.delete_recipe_use_case import DeleteRecipeUseCase
from app.recipes.application.use_cases.get_recipe_use_case import GetRecipeUseCase
from app.recipes.application.use_cases.list_my_recipes_use_case import ListMyRecipesUseCase
from app.recipes.application.use_cases.list_personalizations_use_case import ListPersonalizationsUseCase
from app.recipes.application.use_cases.list_recipe_catalogs_use_cases import ListRecipeTagsUseCase
from app.recipes.application.use_cases.personalize_recipe_use_case import PersonalizeRecipeUseCase
from app.recipes.application.use_cases.recipe_photo_use_cases import (
    AddRecipePhotoUseCase,
    ListRecipePhotosUseCase,
    RemoveRecipePhotoUseCase,
    ReorderCoverPhotosUseCase,
)
from app.recipes.application.use_cases.replace_recipe_equipment_use_case import ReplaceRecipeEquipmentUseCase
from app.recipes.application.use_cases.replace_recipe_ingredients_use_case import ReplaceRecipeIngredientsUseCase
from app.recipes.application.use_cases.replace_recipe_steps_use_case import ReplaceRecipeStepsUseCase
from app.recipes.application.use_cases.replace_recipe_tags_use_case import ReplaceRecipeTagsUseCase
from app.recipes.application.use_cases.search_public_recipes_use_case import SearchPublicRecipesUseCase
from app.recipes.application.use_cases.update_recipe_use_case import UpdateRecipeUseCase
from app.recipes.domain.exceptions import (
    DifficultyNotFoundError,
    RecipeAccessDeniedError,
    RecipeCategoryNotFoundError,
    RecipeNotFoundError,
    RecipePhotoNotFoundError,
    RecipeStepNotFoundError,
    RecipeTagNotFoundError,
    ReferencedEquipmentNotFoundError,
    ReferencedIngredientNotFoundError,
    ReferencedUnitNotFoundError,
)
from app.recipes.domain.value_objects.recipe_id import RecipeId
from app.shared.exceptions.domain_exceptions import ValidationError
from tests.recipes.fakes import RecipesWorld

AUTHOR, FAN, STRANGER = "author", "fan", "stranger"
URL = "https://img.example/{}.jpg"


@pytest.fixture
def world():
    return RecipesWorld()


def create_dto(world: RecipesWorld, **overrides) -> CreateRecipeDTO:
    data = dict(
        user_id=AUTHOR,
        title="Brownies",
        category_id=str(world.cakes.id),
        difficulty_id=str(world.easy.id),
        is_public=True,
        ingredients=[
            RecipeIngredientInputDTO(world.flour.upper(), Decimal("250"), world.grams),
            RecipeIngredientInputDTO(world.egg, Decimal("3"), world.units),
        ],
        equipment=[RecipeEquipmentInputDTO(world.mold)],
        tag_ids=[str(world.chocolate.id)],
        steps=[RecipeStepInputDTO("Mezclar"), RecipeStepInputDTO("Hornear", timer_seconds=1800)],
    )
    data.update(overrides)
    return CreateRecipeDTO(**data)


async def create(world: RecipesWorld, **overrides):
    return await CreateRecipeUseCase(world.recipes, world.validator, world.assembler).execute(
        create_dto(world, **overrides)
    )


class TestCreateAndGet:

    async def test_create_returns_full_detail(self, world):
        detail = await create(world)

        assert detail.is_owner is True
        assert str(detail.category.name) == "Tortas"
        assert str(detail.difficulty.name) == "Fácil"
        assert [str(t.name) for t in detail.tags] == ["chocolate"]
        assert [(str(i.ingredient_name), i.unit_abbreviation, i.position) for i in detail.ingredients] == [
            ("Harina", "g", 1),
            ("Huevo", "u", 2),
        ]
        assert detail.ingredients[0].ingredient_id == world.flour  # stored in canonical form
        assert [str(e.equipment_name) for e in detail.equipment] == ["Molde"]
        assert [(s.step_number, s.timer_seconds) for s in detail.steps] == [(1, None), (2, 1800)]

    @pytest.mark.parametrize(
        "overrides, error",
        [
            ({"category_id": "garbage"}, RecipeCategoryNotFoundError),
            ({"difficulty_id": str(RecipeId())}, DifficultyNotFoundError),
            ({"tag_ids": ["garbage"]}, RecipeTagNotFoundError),
            ({"tag_ids": [str(RecipeId())]}, RecipeTagNotFoundError),
            ({"equipment": [RecipeEquipmentInputDTO("garbage")]}, ReferencedEquipmentNotFoundError),
        ],
    )
    async def test_rejects_unknown_references(self, world, overrides, error):
        with pytest.raises(error):
            await create(world, **overrides)
        assert world.recipes.items == {}

    async def test_rejects_unknown_ingredient_and_unit(self, world):
        with pytest.raises(ReferencedIngredientNotFoundError):
            await create(world, ingredients=[RecipeIngredientInputDTO("nope", Decimal("1"), world.grams)])
        with pytest.raises(ReferencedUnitNotFoundError):
            await create(world, ingredients=[RecipeIngredientInputDTO(world.flour, Decimal("1"), "nope")])

    async def test_get_respects_visibility(self, world):
        public = await create(world)
        private = await create(world, is_public=False)
        get = GetRecipeUseCase(world.recipes, world.assembler)

        assert (await get.execute(public.id, STRANGER)).is_owner is False
        assert (await get.execute(private.id, AUTHOR)).id == private.id
        for recipe_id in (private.id, "garbage", str(RecipeId())):
            with pytest.raises(RecipeNotFoundError):
                await get.execute(recipe_id, STRANGER)

    async def test_get_shows_quantities_as_written_by_default(self, world):
        recipe = await create(world)
        detail = await GetRecipeUseCase(world.recipes, world.assembler).execute(recipe.id, STRANGER)

        assert detail.unit_system == "original"
        assert [(i.display_quantity, i.display_unit_abbreviation, i.converted) for i in detail.ingredients] == [
            (Decimal("250"), "g", False),
            (Decimal("3"), "u", False),
        ]

    async def test_get_displays_quantities_in_unit_system_without_touching_originals(self, world):
        recipe = await create(world)
        detail = await GetRecipeUseCase(world.recipes, world.assembler).execute(recipe.id, STRANGER, "us")

        assert detail.unit_system == "us"
        assert [(i.display_quantity, i.display_unit_abbreviation, i.converted) for i in detail.ingredients] == [
            (Decimal("125"), "cup", True),
            (Decimal("1.5"), "cup", True),
        ]
        # The editor and preparation read these: they stay as the author wrote them.
        assert [(i.quantity, i.unit_id, i.unit_abbreviation) for i in detail.ingredients] == [
            (Decimal("250"), world.grams, "g"),
            (Decimal("3"), world.units, "u"),
        ]
        stored = await RecipeQueryService(world.recipes, world.assembler, world.categories, world.tags).get_detail(
            recipe.id, STRANGER
        )
        assert stored.unit_system == "original"


class TestOwnership:

    @pytest.fixture
    async def recipe(self, world):
        return await create(world)

    async def test_strangers_get_403_on_public_recipe(self, world, recipe):
        with pytest.raises(RecipeAccessDeniedError):
            await UpdateRecipeUseCase(world.recipes, world.validator, world.assembler).execute(
                UpdateRecipeDTO(STRANGER, recipe.id, {"title": "Hackeada"})
            )

    async def test_strangers_get_404_on_private_recipe(self, world):
        private = await create(world, is_public=False)
        with pytest.raises(RecipeNotFoundError):
            await DeleteRecipeUseCase(world.recipes).execute(STRANGER, private.id)

    async def test_update_only_touches_sent_fields(self, world, recipe):
        detail = await UpdateRecipeUseCase(world.recipes, world.validator, world.assembler).execute(
            UpdateRecipeDTO(AUTHOR, recipe.id, {"servings": 6, "category_id": None, "created_by_user_id": "evil"})
        )
        assert detail.servings == 6
        assert detail.category is None
        assert detail.created_by_user_id == AUTHOR
        assert detail.title == "Brownies"

    async def test_update_validates_references(self, world, recipe):
        with pytest.raises(DifficultyNotFoundError):
            await UpdateRecipeUseCase(world.recipes, world.validator, world.assembler).execute(
                UpdateRecipeDTO(AUTHOR, recipe.id, {"difficulty_id": "garbage"})
            )

    async def test_delete_hides_recipe(self, world, recipe):
        await DeleteRecipeUseCase(world.recipes).execute(AUTHOR, recipe.id)

        with pytest.raises(RecipeNotFoundError):
            await GetRecipeUseCase(world.recipes, world.assembler).execute(recipe.id, AUTHOR)
        assert (await ListMyRecipesUseCase(world.recipes, world.assembler).execute(AUTHOR)).total == 0

    async def test_replace_lists(self, world, recipe):
        ingredients = await ReplaceRecipeIngredientsUseCase(world.recipes, world.validator, world.assembler).execute(
            AUTHOR, recipe.id, [RecipeIngredientInputDTO(world.egg, Decimal("6"), world.units)]
        )
        equipment = await ReplaceRecipeEquipmentUseCase(world.recipes, world.validator, world.assembler).execute(
            AUTHOR, recipe.id, []
        )
        tags = await ReplaceRecipeTagsUseCase(world.recipes, world.validator, world.assembler).execute(
            AUTHOR, recipe.id, [str(world.vegan.id), str(world.chocolate.id)]
        )

        assert [(str(i.ingredient_name), i.quantity) for i in ingredients.ingredients] == [("Huevo", Decimal("6"))]
        assert equipment.equipment == []
        assert [str(t.name) for t in tags.tags] == ["chocolate", "vegano"]

    async def test_replace_steps_keeps_identified_step(self, world, recipe):
        bake_id = recipe.steps[1].id
        steps = ReplaceRecipeStepsUseCase(world.recipes, world.assembler)

        detail = await steps.execute(
            AUTHOR, recipe.id, [RecipeStepInputDTO("Hornear 25 min", id=bake_id.upper()), RecipeStepInputDTO("Enfriar")]
        )

        assert [(s.id, s.step_number) for s in detail.steps][0] == (bake_id, 1)
        with pytest.raises(RecipeStepNotFoundError):
            await steps.execute(AUTHOR, recipe.id, [RecipeStepInputDTO("x", id="garbage")])


class TestPersonalization:

    async def test_personalize_and_list(self, world):
        original = await create(world)
        personalize = PersonalizeRecipeUseCase(world.recipes, world.assembler)

        copy = await personalize.execute(FAN, original.id, title="Brownies sin TACC")
        await personalize.execute(FAN, original.id)

        assert copy.is_personalization is True
        assert copy.is_public is False
        assert copy.source_recipe_title == "Brownies"
        assert copy.source_updated_since_personalized is False
        page = await ListPersonalizationsUseCase(world.recipes, world.assembler).execute(FAN, original.id)
        assert page.total == 2
        assert (await ListPersonalizationsUseCase(world.recipes, world.assembler).execute(STRANGER, original.id)).total == 0

    async def test_flags_original_changes(self, world):
        original = await create(world)
        copy = await PersonalizeRecipeUseCase(world.recipes, world.assembler).execute(FAN, original.id)
        stored_original = world.recipes.items[RecipeId.from_string(original.id)]
        stored_original.updated_at += timedelta(minutes=5)

        detail = await GetRecipeUseCase(world.recipes, world.assembler).execute(copy.id, FAN)

        assert detail.source_updated_since_personalized is True

    async def test_hidden_original_is_not_revealed(self, world):
        original = await create(world)
        copy = await PersonalizeRecipeUseCase(world.recipes, world.assembler).execute(FAN, original.id)
        await UpdateRecipeUseCase(world.recipes, world.validator, world.assembler).execute(
            UpdateRecipeDTO(AUTHOR, original.id, {"is_public": False})
        )

        detail = await GetRecipeUseCase(world.recipes, world.assembler).execute(copy.id, FAN)

        assert detail.source_recipe_title is None
        assert detail.source_recipe_id == original.id

    async def test_cannot_personalize_private_recipe_of_others(self, world):
        private = await create(world, is_public=False)
        with pytest.raises(RecipeNotFoundError):
            await PersonalizeRecipeUseCase(world.recipes, world.assembler).execute(FAN, private.id)

    async def test_list_my_recipes_by_kind(self, world):
        original = await create(world, user_id=FAN)
        await PersonalizeRecipeUseCase(world.recipes, world.assembler).execute(FAN, original.id)
        mine = ListMyRecipesUseCase(world.recipes, world.assembler)

        assert (await mine.execute(FAN)).total == 2
        assert [r.is_personalization for r in (await mine.execute(FAN, kind="original")).items] == [False]
        assert [r.is_personalization for r in (await mine.execute(FAN, kind="personalized")).items] == [True]


class TestPhotos:

    @pytest.fixture
    async def recipe(self, world):
        return await create(world)

    def add(self, world):
        return AddRecipePhotoUseCase(world.recipes)

    async def test_add_list_reorder_remove(self, world, recipe):
        a = await self.add(world).execute(AddRecipePhotoDTO(AUTHOR, recipe.id, "cover", URL.format("a")))
        b = await self.add(world).execute(AddRecipePhotoDTO(AUTHOR, recipe.id, "cover", URL.format("b")))
        step = await self.add(world).execute(
            AddRecipePhotoDTO(AUTHOR, recipe.id, "step", URL.format("s"), step_id=recipe.steps[0].id)
        )

        listed = await ListRecipePhotosUseCase(world.recipes).execute(STRANGER, recipe.id)
        assert [p.id for p in listed] == [a.id, b.id, step.id]

        reordered = await ReorderCoverPhotosUseCase(world.recipes).execute(AUTHOR, recipe.id, [b.id, a.id])
        assert [p.id for p in reordered] == [b.id, a.id]

        await RemoveRecipePhotoUseCase(world.recipes).execute(AUTHOR, recipe.id, b.id)
        listed = await ListRecipePhotosUseCase(world.recipes).execute(AUTHOR, recipe.id)
        assert [(p.id, p.position) for p in listed if p.photo_type == "cover"] == [(a.id, 1)]

    @pytest.mark.parametrize(
        "photo_type, step_id, error",
        [
            ("cover", "any", ValidationError),
            ("step", None, ValidationError),
            ("step", "garbage", RecipeStepNotFoundError),
            ("video", None, ValidationError),
        ],
    )
    async def test_add_validation(self, world, recipe, photo_type, step_id, error):
        with pytest.raises(error):
            await self.add(world).execute(AddRecipePhotoDTO(AUTHOR, recipe.id, photo_type, URL.format("x"), step_id))

    async def test_only_owner_adds_photos(self, world, recipe):
        with pytest.raises(RecipeAccessDeniedError):
            await self.add(world).execute(AddRecipePhotoDTO(STRANGER, recipe.id, "cover", URL.format("x")))

    @pytest.mark.parametrize("bad", ["garbage", str(RecipeId())])
    async def test_remove_unknown_photo(self, world, recipe, bad):
        with pytest.raises(RecipePhotoNotFoundError):
            await RemoveRecipePhotoUseCase(world.recipes).execute(AUTHOR, recipe.id, bad)


class TestSearch:

    async def test_malformed_filters_match_nothing_without_querying(self, world):
        await create(world)
        search = SearchPublicRecipesUseCase(world.recipes, world.assembler)

        for dto in (
            SearchRecipesDTO(category_id="garbage"),
            SearchRecipesDTO(difficulty_id="garbage"),
            SearchRecipesDTO(ingredient_ids=["garbage"]),
            SearchRecipesDTO(tag_ids=["garbage"]),
        ):
            page = await search.execute(dto, STRANGER)
            assert (page.items, page.total) == ([], 0)
        assert world.recipes.last_search is None

    async def test_ingredient_filter_is_case_insensitive(self, world):
        await create(world)

        page = await SearchPublicRecipesUseCase(world.recipes, world.assembler).execute(
            SearchRecipesDTO(ingredient_ids=[world.flour.upper()]), STRANGER
        )

        assert page.total == 1

    async def test_only_public_recipes(self, world):
        await create(world, title="Pública")
        await create(world, title="Privada", is_public=False)

        page = await SearchPublicRecipesUseCase(world.recipes, world.assembler).execute(
            SearchRecipesDTO(query="  a "), AUTHOR
        )

        assert [r.title for r in page.items] == ["Pública"]
        assert world.recipes.last_search.query == "a"


class TestCatalogs:

    async def test_tags_grouped_then_alphabetical(self, world):
        tags = await ListRecipeTagsUseCase(world.tags).execute()
        assert [(t.group, str(t.name)) for t in tags] == [("sabor", "chocolate"), ("dieta", "vegano"), ("celebraciones", "Navidad")]

    async def test_tags_of_one_group(self, world):
        assert [str(t.name) for t in await ListRecipeTagsUseCase(world.tags).execute("dieta")] == ["vegano"]


class TestRecipeQueryService:

    @pytest.fixture
    def service(self, world):
        return RecipeQueryService(world.recipes, world.assembler, world.categories, world.tags)

    async def test_visibility(self, world, service):
        public = await create(world, title="Pública")
        private = await create(world, title="Privada", is_public=False)

        assert await service.get_visible(private.id, STRANGER) is None
        assert (await service.get_visible(private.id, AUTHOR)).id == private.id
        assert [r.id for r in await service.get_many_visible([public.id, private.id, "garbage"], STRANGER)] == [public.id]
        assert await service.get_detail("garbage", AUTHOR) is None

    async def test_compositions_keep_order_and_accept_any_case(self, world, service):
        a = await create(world, title="A")
        b = await create(world, title="B")

        result = await service.get_compositions([b.id.upper(), a.id, b.id], STRANGER)

        assert [c.recipe.id for c in result] == [b.id, a.id]
        assert result[0].ingredient_ids == sorted([world.flour, world.egg])
        assert result[0].equipment_ids == [world.mold]

    async def test_rank_with_malformed_filters_matches_nothing(self, world, service):
        query = IngredientOverlapQueryDTO(STRANGER, [world.flour], [], 0.8, 0.2, tag_ids=["garbage"])

        result = await service.rank_by_ingredient_overlap(query)

        assert (result.recipe_ids, result.total) == ([], 0)
        assert world.recipes.last_overlap_query is None

    async def test_rank_drops_malformed_exclusions(self, world, service):
        excluded = str(RecipeId())
        await service.rank_by_ingredient_overlap(
            IngredientOverlapQueryDTO(STRANGER, [world.flour], [], 0.8, 0.2, excluded_recipe_ids=[excluded, "garbage"])
        )
        assert [str(i) for i in world.recipes.last_overlap_query.excluded_recipe_ids] == [excluded]
