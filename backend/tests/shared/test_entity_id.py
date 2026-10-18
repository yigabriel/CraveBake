import uuid

import pytest

from app.shared.domain.value_objects.entity_id import EntityId


class OtherId(EntityId):
    pass


class TestEntityId:

    def test_round_trip(self):
        entity_id = EntityId()
        assert EntityId.from_string(str(entity_id)) == entity_id

    @pytest.mark.parametrize("raw", ["garbage", "", None, 123])
    def test_try_from_string_returns_none_for_malformed(self, raw):
        assert EntityId.try_from_string(raw) is None

    def test_try_from_string_keeps_subclass(self):
        parsed = OtherId.try_from_string(str(uuid.uuid4()))
        assert isinstance(parsed, OtherId)

    def test_subclasses_with_same_uuid_are_not_equal(self):
        raw = uuid.uuid4()
        assert EntityId(raw) != OtherId(raw)
