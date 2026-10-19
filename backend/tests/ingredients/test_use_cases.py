from decimal import Decimal

import pytest

from app.ingredients.application.dto.convert_measurement_dto import ConvertMeasurementDTO
from app.ingredients.application.dto.display_quantity_dto import QuantityToDisplayDTO
from app.ingredients.application.dto.ingredient_dto import CreateIngredientDTO, SearchIngredientsDTO
from app.ingredients.application.dto.user_ingredient_dto import UpsertUserIngredientDTO
from app.ingredients.application.public.ingredient_query_service import IngredientQueryService
from app.ingredients.application.use_cases.convert_measurement_use_case import ConvertMeasurementUseCase
from app.ingredients.application.use_cases.create_ingredient_use_case import CreateIngredientUseCase
from app.ingredients.application.use_cases.get_ingredient_use_case import GetIngredientUseCase
from app.ingredients.application.use_cases.list_categories_use_case import ListCategoriesUseCase
from app.ingredients.application.use_cases.list_units_use_case import ListUnitsUseCase
from app.ingredients.application.use_cases.list_user_ingredients_use_case import ListUserIngredientsUseCase
from app.ingredients.application.use_cases.remove_user_ingredient_use_case import RemoveUserIngredientUseCase
from app.ingredients.application.use_cases.search_ingredients_use_case import SearchIngredientsUseCase
from app.ingredients.application.use_cases.upsert_user_ingredient_use_case import UpsertUserIngredientUseCase
from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.entities.user_ingredient import UserIngredient
from app.ingredients.domain.exceptions import (
    ConversionNotAvailableError,
    IngredientAlreadyExistsError,
    IngredientNotFoundError,
    UnitNotFoundError,
)
from app.ingredients.domain.services.measurement_converter import MeasurementConverter
from app.ingredients.domain.services.unit_system_converter import UnitSystemConverter
from app.ingredients.domain.value_objects.ingredient_id import IngredientId
from app.ingredients.domain.value_objects.quantity import Quantity
from app.shared.exceptions.domain_exceptions import ValidationError
from tests.ingredients.fakes import (
    InMemoryConversionRepository,
    InMemoryIngredientRepository,
    InMemoryUnitRepository,
    InMemoryUserIngredientRepository,
    conversion,
    seed_units,
)

D = Decimal
USER = "user-1"


@pytest.fixture
def units():
    return seed_units()


@pytest.fixture
def unit_repo(units):
    return InMemoryUnitRepository(units)


@pytest.fixture
def ingredients():
    return InMemoryIngredientRepository()


@pytest.fixture
def conversions():
    return InMemoryConversionRepository()


@pytest.fixture
def pantry():
    return InMemoryUserIngredientRepository()


@pytest.fixture
async def flour(ingredients, conversions, units):
    item = Ingredient.create("Harina todo uso (0000)", default_category="harinas")
    await ingredients.add(item)
    await conversions.add(conversion(item, units["cup"], "125"))
    return item


@pytest.fixture
async def sugar(ingredients):
    item = Ingredient.create("Azúcar", default_category="azúcares")
    await ingredients.add(item)
    return item


class TestDomain:

    @pytest.mark.parametrize("raw", ["0", "-1"])
    def test_quantity_must_be_positive(self, raw):
        with pytest.raises(ValidationError):
            Quantity(D(raw))

    def test_ingredient_name_is_cleaned_and_required(self):
        assert Ingredient.create("  Manteca ").name.text == "Manteca"
        with pytest.raises(ValidationError):
            Ingredient.create("   ")

    def test_name_is_written_in_the_creators_language(self):
        item = Ingredient.create("Butter", language="en")
        assert (item.name.original, item.name.in_("es")) == ("en", "Butter")

    def test_translate_keeps_the_original(self):
        item = Ingredient.create("Manteca")
        item.translate("en", " Butter ")
        assert (item.name.in_("en"), item.name.in_("es"), item.name.original) == ("Butter", "Manteca", "es")


class TestCatalog:

    async def test_create_and_get(self, ingredients):
        created = await CreateIngredientUseCase(ingredients).execute(CreateIngredientDTO(name="Cacao"))
        fetched = await GetIngredientUseCase(ingredients).execute(created.id)
        assert fetched.name.text == "Cacao"

    async def test_create_keeps_the_creators_language(self, ingredients):
        created = await CreateIngredientUseCase(ingredients).execute(CreateIngredientDTO(name="Cardamom", language="en"))
        assert (created.name.original, created.name.in_("es")) == ("en", "Cardamom")

    async def test_duplicate_name_in_another_language(self, ingredients, flour):
        flour.translate("en", "All-purpose flour")
        with pytest.raises(IngredientAlreadyExistsError):
            await CreateIngredientUseCase(ingredients).execute(CreateIngredientDTO(name="all-purpose FLOUR", language="en"))

    async def test_duplicate_name(self, ingredients, flour):
        with pytest.raises(IngredientAlreadyExistsError):
            await CreateIngredientUseCase(ingredients).execute(CreateIngredientDTO(name=" harina TODO uso (0000) "))

    @pytest.mark.parametrize("raw", ["garbage", str(IngredientId())])
    async def test_get_unknown(self, ingredients, raw):
        with pytest.raises(IngredientNotFoundError):
            await GetIngredientUseCase(ingredients).execute(raw)

    async def test_search(self, ingredients, flour, sugar):
        page = await SearchIngredientsUseCase(ingredients).execute(SearchIngredientsDTO(query="har"))
        assert [i.name for i in page.items] == [flour.name]
        assert page.total == 1

    async def test_search_matches_any_language(self, ingredients, flour, sugar):
        flour.translate("en", "All-purpose flour")
        page = await SearchIngredientsUseCase(ingredients).execute(SearchIngredientsDTO(query="FLOUR"))
        assert [i.id for i in page.items] == [str(flour.id)]

    async def test_categories(self, ingredients, flour, sugar):
        await ingredients.add(Ingredient.create("Harina integral", default_category="harinas"))
        await ingredients.add(Ingredient.create("Sin categoría"))

        result = await ListCategoriesUseCase(ingredients).execute()

        assert [(c.name, str(c.label), c.ingredient_count) for c in result] == [("azúcares", "azúcares", 1), ("harinas", "harinas", 2)]

    async def test_list_units(self, unit_repo):
        result = await ListUnitsUseCase(unit_repo).execute()
        assert {u.abbreviation for u in result} >= {"g", "cup", "u"}


class TestConvertMeasurement:

    @pytest.fixture
    def use_case(self, unit_repo, conversions):
        return ConvertMeasurementUseCase(unit_repo, conversions, MeasurementConverter())

    async def test_cups_of_flour_to_grams(self, use_case, units, flour):
        result = await use_case.execute(
            ConvertMeasurementDTO(D("2"), str(units["cup"].id), str(units["g"].id), str(flour.id))
        )
        assert result.converted_quantity == D("250")
        assert (result.from_unit.abbreviation, result.to_unit.abbreviation) == ("cup", "g")

    @pytest.mark.parametrize(
        "quantity, source, target, expected",
        [
            ("1", "l", "g", "528.34"),  # 1000 ml / 236.588 * 125 g
            ("500", "g", "ml", "946.35"),
            ("1", "tsp", "g", "2.60"),  # derived from the cup figure, no tsp figure seeded here
        ],
    )
    async def test_volume_without_own_figure_derives_from_cup(self, use_case, units, flour, quantity, source, target, expected):
        result = await use_case.execute(
            ConvertMeasurementDTO(D(quantity), str(units[source].id), str(units[target].id), str(flour.id))
        )
        assert round(result.converted_quantity, 2) == D(expected)

    async def test_exact_measure_figure_wins_over_cup(self, use_case, units, flour, conversions):
        # Butter-like case: the tbsp figure is not cup/16 and must be used as is.
        await conversions.add(conversion(flour, units["tbsp"], "10"))

        result = await use_case.execute(
            ConvertMeasurementDTO(D("2"), str(units["tbsp"].id), str(units["g"].id), str(flour.id))
        )

        assert result.converted_quantity == D("20")

    async def test_derives_from_biggest_measure(self, use_case, units, flour, conversions):
        await conversions.add(conversion(flour, units["tsp"], "3"))  # rougher figure, must not be chosen

        result = await use_case.execute(
            ConvertMeasurementDTO(D("236.588"), str(units["ml"].id), str(units["g"].id), str(flour.id))
        )

        assert result.converted_quantity == D("125")

    async def test_same_type_ignores_ingredient(self, use_case, units):
        result = await use_case.execute(
            ConvertMeasurementDTO(D("2"), str(units["kg"].id), str(units["g"].id), "garbage")
        )
        assert result.converted_quantity == D("2000")

    async def test_ingredient_without_ratio(self, use_case, units, sugar):
        with pytest.raises(ConversionNotAvailableError):
            await use_case.execute(
                ConvertMeasurementDTO(D("1"), str(units["cup"].id), str(units["g"].id), str(sugar.id))
            )

    @pytest.mark.parametrize("bad", ["garbage", str(IngredientId())])
    async def test_unknown_or_malformed_unit_is_not_found(self, use_case, units, bad):
        with pytest.raises(UnitNotFoundError):
            await use_case.execute(ConvertMeasurementDTO(D("1"), bad, str(units["g"].id)))
        with pytest.raises(UnitNotFoundError):
            await use_case.execute(ConvertMeasurementDTO(D("1"), str(units["g"].id), bad))


class TestPantry:

    @pytest.fixture
    def upsert(self, pantry, ingredients, unit_repo):
        return UpsertUserIngredientUseCase(pantry, ingredients, unit_repo)

    async def test_upsert_creates_then_updates(self, upsert, pantry, flour, units):
        await upsert.execute(UpsertUserIngredientDTO(USER, str(flour.id)))
        result = await upsert.execute(
            UpsertUserIngredientDTO(USER, str(flour.id), quantity=D("500"), unit_id=str(units["g"].id))
        )

        assert len(pantry.items) == 1
        assert result.quantity == D("500")
        assert result.unit.abbreviation == "g"

    async def test_upsert_rejects_non_positive_quantity(self, upsert, flour):
        with pytest.raises(ValidationError):
            await upsert.execute(UpsertUserIngredientDTO(USER, str(flour.id), quantity=D("0")))

    @pytest.mark.parametrize("bad", ["garbage", str(IngredientId())])
    async def test_upsert_unknown_ingredient(self, upsert, bad):
        with pytest.raises(IngredientNotFoundError):
            await upsert.execute(UpsertUserIngredientDTO(USER, bad))

    @pytest.mark.parametrize("bad", ["garbage", str(IngredientId())])
    async def test_upsert_unknown_unit(self, upsert, flour, bad):
        with pytest.raises(UnitNotFoundError):
            await upsert.execute(UpsertUserIngredientDTO(USER, str(flour.id), unit_id=bad))

    async def test_list_only_own_and_skips_orphans(self, upsert, pantry, ingredients, unit_repo, flour, sugar, units):
        await upsert.execute(UpsertUserIngredientDTO(USER, str(flour.id), D("1"), str(units["cup"].id)))
        await upsert.execute(UpsertUserIngredientDTO("other", str(sugar.id)))
        await pantry.add(UserIngredient.register(USER, IngredientId()))  # orphan

        result = await ListUserIngredientsUseCase(pantry, ingredients, unit_repo).execute(USER)

        assert [(r.ingredient.name, r.unit.abbreviation) for r in result] == [(flour.name, "cup")]

    async def test_remove(self, upsert, pantry, flour):
        await upsert.execute(UpsertUserIngredientDTO(USER, str(flour.id)))

        await RemoveUserIngredientUseCase(pantry).execute(USER, str(flour.id))

        assert pantry.items == []

    async def test_remove_malformed_id_is_noop(self, pantry):
        await RemoveUserIngredientUseCase(pantry).execute(USER, "garbage")


class TestIngredientQueryService:

    @pytest.fixture
    def service(self, ingredients, unit_repo, pantry, conversions):
        return IngredientQueryService(ingredients, unit_repo, pantry, conversions, UnitSystemConverter())

    async def test_get_ingredients_and_units_skip_bad_ids(self, service, flour, units):
        assert [i.id for i in await service.get_ingredients([str(flour.id), "garbage", str(flour.id)])] == [str(flour.id)]
        assert [u.abbreviation for u in await service.get_units([str(units["g"].id), "garbage"])] == ["g"]

    async def test_pantry_ids(self, service, pantry, flour):
        await pantry.add(UserIngredient.register(USER, flour.id))
        assert await service.list_pantry_ingredient_ids(USER) == [str(flour.id)]

    async def test_display_in_unit_system(self, service, flour, units):
        result = await service.display_in_unit_system(
            [
                QuantityToDisplayDTO(str(flour.id), D("2"), str(units["cup"].id)),
                QuantityToDisplayDTO(str(flour.id), D("3"), str(units["u"].id)),
                QuantityToDisplayDTO(str(flour.id), D("1"), "garbage"),
            ],
            "metric",
        )

        assert [(r.quantity, r.unit_abbreviation, r.converted) for r in result] == [
            (D("250"), "g", True),
            (D("3"), "u", False),
            (D("1"), "", False),
        ]

    async def test_display_matches_ingredient_id_in_any_case(self, service, flour, units):
        result = await service.display_in_unit_system(
            [QuantityToDisplayDTO(str(flour.id).upper(), D("1"), str(units["cup"].id))], "metric"
        )
        assert (result[0].quantity, result[0].unit_abbreviation) == (D("125"), "g")
