import pytest

from app.equipment.application.dto.equipment_dto import (
    CreateEquipmentDTO,
    SearchEquipmentDTO,
    UpsertUserEquipmentDTO,
)
from app.equipment.application.public.equipment_query_service import EquipmentQueryService
from app.equipment.application.use_cases.equipment_catalog_use_cases import (
    CreateEquipmentUseCase,
    GetEquipmentUseCase,
    SearchEquipmentUseCase,
)
from app.equipment.application.use_cases.user_equipment_use_cases import (
    ListUserEquipmentUseCase,
    RemoveUserEquipmentUseCase,
    UpsertUserEquipmentUseCase,
)
from app.equipment.domain.entities.equipment import Equipment, EquipmentType
from app.equipment.domain.entities.user_equipment import UserEquipment
from app.equipment.domain.exceptions import EquipmentAlreadyExistsError, EquipmentNotFoundError
from app.equipment.domain.value_objects.equipment_id import EquipmentId
from app.shared.exceptions.domain_exceptions import ValidationError
from tests.equipment.fakes import InMemoryEquipmentRepository, InMemoryUserEquipmentRepository

USER = "user-1"


@pytest.fixture
def catalog():
    return InMemoryEquipmentRepository()


@pytest.fixture
def kitchen():
    return InMemoryUserEquipmentRepository()


@pytest.fixture
async def mixer(catalog):
    item = Equipment.create("Batidora planetaria", EquipmentType.ELECTRODOMESTICO)
    await catalog.add(item)
    return item


@pytest.fixture
async def mold(catalog):
    item = Equipment.create("Molde redondo 20cm", EquipmentType.MOLDE)
    await catalog.add(item)
    return item


class TestEquipmentEntity:

    def test_create_cleans_fields(self):
        item = Equipment.create("  Espátula  ", EquipmentType.UTENSILIO, description="   ")
        assert item.name.text == "Espátula"
        assert item.description is None

    @pytest.mark.parametrize("name", ["", "   ", None])
    def test_rejects_empty_name(self, name):
        with pytest.raises(ValidationError):
            Equipment.create(name, EquipmentType.OTRO)


class TestUserEquipmentEntity:

    def test_register_defaults(self):
        item = UserEquipment.register(USER, EquipmentId(), notes="  ")
        assert item.quantity == 1
        assert item.notes is None

    @pytest.mark.parametrize("quantity", [0, -1])
    def test_rejects_quantity_below_one(self, quantity):
        with pytest.raises(ValidationError):
            UserEquipment.register(USER, EquipmentId(), quantity=quantity)

    def test_update_validates_quantity(self):
        item = UserEquipment.register(USER, EquipmentId())
        with pytest.raises(ValidationError):
            item.update(0, None)
        assert item.quantity == 1

    def test_update_changes_fields(self):
        item = UserEquipment.register(USER, EquipmentId())
        item.update(3, " dos rotos ")
        assert (item.quantity, item.notes) == (3, "dos rotos")


class TestCatalogUseCases:

    async def test_create(self, catalog):
        result = await CreateEquipmentUseCase(catalog).execute(
            CreateEquipmentDTO(name="Rodillo", equipment_type="utensilio")
        )
        assert result.name.text == "Rodillo"
        assert result.equipment_type == "utensilio"
        assert len(catalog.items) == 1

    async def test_create_rejects_duplicate_name_case_insensitive(self, catalog, mixer):
        with pytest.raises(EquipmentAlreadyExistsError):
            await CreateEquipmentUseCase(catalog).execute(
                CreateEquipmentDTO(name="  batidora PLANETARIA ", equipment_type="electrodomestico")
            )

    async def test_get(self, catalog, mixer):
        result = await GetEquipmentUseCase(catalog).execute(str(mixer.id))
        assert result.id == str(mixer.id)

    @pytest.mark.parametrize("raw", ["not-a-uuid", str(EquipmentId())])
    async def test_get_unknown_or_malformed_is_not_found(self, catalog, raw):
        with pytest.raises(EquipmentNotFoundError):
            await GetEquipmentUseCase(catalog).execute(raw)

    async def test_search_filters_by_type_and_paginates(self, catalog, mixer, mold):
        page = await SearchEquipmentUseCase(catalog).execute(SearchEquipmentDTO(equipment_type="molde"))
        assert [item.name.text for item in page.items] == ["Molde redondo 20cm"]
        assert page.total == 1

        page = await SearchEquipmentUseCase(catalog).execute(SearchEquipmentDTO(limit=1, offset=1))
        assert len(page.items) == 1
        assert page.total == 2
        assert (page.limit, page.offset) == (1, 1)


class TestKitchenUseCases:

    async def test_upsert_creates_then_updates_same_entry(self, catalog, kitchen, mixer):
        use_case = UpsertUserEquipmentUseCase(kitchen, catalog)

        await use_case.execute(UpsertUserEquipmentDTO(user_id=USER, equipment_id=str(mixer.id)))
        result = await use_case.execute(
            UpsertUserEquipmentDTO(user_id=USER, equipment_id=str(mixer.id), quantity=2, notes="roja")
        )

        assert len(kitchen.items) == 1
        assert (result.quantity, result.notes) == (2, "roja")
        assert result.equipment.name.text == "Batidora planetaria"

    async def test_upsert_unknown_equipment(self, catalog, kitchen):
        with pytest.raises(EquipmentNotFoundError):
            await UpsertUserEquipmentUseCase(kitchen, catalog).execute(
                UpsertUserEquipmentDTO(user_id=USER, equipment_id="garbage")
            )

    async def test_list_only_own_and_skips_orphans(self, catalog, kitchen, mixer, mold):
        upsert = UpsertUserEquipmentUseCase(kitchen, catalog)
        await upsert.execute(UpsertUserEquipmentDTO(user_id=USER, equipment_id=str(mixer.id)))
        await upsert.execute(UpsertUserEquipmentDTO(user_id="other", equipment_id=str(mold.id)))
        await kitchen.add(UserEquipment.register(USER, EquipmentId()))  # orphan row

        result = await ListUserEquipmentUseCase(kitchen, catalog).execute(USER)

        assert [item.equipment.id for item in result] == [str(mixer.id)]

    async def test_remove(self, catalog, kitchen, mixer):
        await UpsertUserEquipmentUseCase(kitchen, catalog).execute(
            UpsertUserEquipmentDTO(user_id=USER, equipment_id=str(mixer.id))
        )

        await RemoveUserEquipmentUseCase(kitchen).execute(USER, str(mixer.id))

        assert kitchen.items == []

    async def test_remove_malformed_id_is_noop(self, kitchen):
        await RemoveUserEquipmentUseCase(kitchen).execute(USER, "garbage")


class TestEquipmentQueryService:

    async def test_get_equipment_skips_unknown_malformed_and_duplicates(self, catalog, kitchen, mixer):
        service = EquipmentQueryService(catalog, kitchen)

        result = await service.get_equipment([str(mixer.id), str(mixer.id), "garbage", str(EquipmentId())])

        assert [item.id for item in result] == [str(mixer.id)]

    async def test_list_user_equipment_ids(self, catalog, kitchen, mixer):
        await kitchen.add(UserEquipment.register(USER, mixer.id))

        assert await EquipmentQueryService(catalog, kitchen).list_user_equipment_ids(USER) == [str(mixer.id)]
