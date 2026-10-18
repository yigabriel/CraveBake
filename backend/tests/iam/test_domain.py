import uuid

import pytest

from app.iam.domain.value_objects.email import Email
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.language_preference import LanguagePreference
from app.iam.domain.value_objects.plain_password import PlainPassword
from app.iam.domain.value_objects.unit_system_preference import UnitSystemPreference
from app.iam.domain.value_objects.user_id import UserId
from app.shared.exceptions.domain_exceptions import ValidationError
from tests.iam.fakes import make_user


class TestEmail:

    def test_normalizes_case_and_whitespace(self):
        assert Email("  Ana@Example.COM ").value == "ana@example.com"

    def test_equal_after_normalization(self):
        assert Email("ANA@example.com") == Email("ana@example.com")

    @pytest.mark.parametrize("raw", ["", "ana", "ana@", "@example.com", "ana@example", "a na@example.com"])
    def test_rejects_invalid(self, raw):
        with pytest.raises(ValidationError):
            Email(raw)


class TestPlainPassword:

    def test_accepts_valid(self):
        assert PlainPassword("Secret123").value == "Secret123"

    @pytest.mark.parametrize(
        "raw, reason",
        [
            ("Ab1", "8 characters"),
            ("Abcdefg1"[:7], "8 characters"),
            ("abcdefgh", "digit"),
            ("12345678", "letter"),
        ],
    )
    def test_rejects_weak(self, raw, reason):
        with pytest.raises(ValidationError, match=reason):
            PlainPassword(raw)


class TestHashedPassword:

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            HashedPassword("")


class TestUserId:

    def test_generates_unique_ids(self):
        assert UserId() != UserId()

    def test_round_trips_through_string(self):
        user_id = UserId()
        assert UserId.from_string(str(user_id)) == user_id

    @pytest.mark.parametrize("raw", ["not-a-uuid", "", "1234"])
    def test_from_string_rejects_invalid(self, raw):
        with pytest.raises(ValidationError):
            UserId.from_string(raw)

    def test_wraps_uuid(self):
        raw = uuid.uuid4()
        assert UserId(raw).value == raw


class TestUser:

    def test_register_sets_defaults(self):
        user = make_user(full_name="  Ana  ")

        assert user.full_name == "Ana"
        assert user.is_active is True
        assert user.avatar_url is None
        assert user.preferred_unit_system is UnitSystemPreference.METRIC
        assert user.preferred_language is LanguagePreference.ENGLISH

    def test_deactivate_and_activate(self):
        user = make_user()

        user.deactivate()
        assert user.is_active is False

        user.activate()
        assert user.is_active is True

    def test_update_profile_only_changes_given_fields(self):
        user = make_user(full_name="Ana")

        user.update_profile(avatar_url="https://img/ana.png")

        assert user.full_name == "Ana"
        assert user.avatar_url == "https://img/ana.png"

    def test_update_profile_strips_name(self):
        user = make_user()
        user.update_profile(full_name="  Ana María ")
        assert user.full_name == "Ana María"

    def test_change_unit_preference(self):
        user = make_user()
        user.change_unit_preference(UnitSystemPreference.US)
        assert user.preferred_unit_system is UnitSystemPreference.US

    def test_change_language_preference(self):
        user = make_user()
        user.change_language_preference("es")
        assert user.preferred_language is LanguagePreference.SPANISH

    def test_change_language_rejects_unknown(self):
        user = make_user()
        with pytest.raises(ValidationError):
            user.change_language_preference("klingon")

    def test_mutations_touch_updated_at(self):
        user = make_user()
        before = user.updated_at

        user.deactivate()

        assert user.updated_at >= before
