import pytest

from app.iam.application.dto.change_password_dto import ChangePasswordDTO
from app.iam.application.dto.login_dto import LoginDTO
from app.iam.application.dto.register_user_dto import RegisterUserDTO
from app.iam.application.dto.update_language_dto import UpdateLanguageDTO
from app.iam.application.dto.update_unit_preference_dto import UpdateUnitPreferenceDTO
from app.iam.application.dto.update_user_dto import UpdateUserDTO
from app.iam.application.use_cases.activate_user_use_case import ActivateUserUseCase
from app.iam.application.use_cases.authenticate_user_use_case import AuthenticateUserUseCase
from app.iam.application.use_cases.change_password_use_case import ChangePasswordUseCase
from app.iam.application.use_cases.deactivate_user_use_case import DeactivateUserUseCase
from app.iam.application.use_cases.get_current_user_use_case import GetCurrentUserUseCase
from app.iam.application.use_cases.register_user_use_case import RegisterUserUseCase
from app.iam.application.use_cases.update_language_use_case import UpdateLanguageUseCase
from app.iam.application.use_cases.update_profile_use_case import UpdateProfileUseCase
from app.iam.application.use_cases.update_unit_preference_use_case import (
    UpdateUnitPreferenceUseCase,
)
from app.iam.domain.exceptions import (
    IncorrectCurrentPasswordError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.iam.domain.value_objects.hashed_password import HashedPassword
from app.iam.domain.value_objects.user_id import UserId
from app.shared.exceptions.domain_exceptions import ValidationError
from tests.iam.fakes import (
    FakePasswordHasher,
    FakeTokenService,
    InMemoryUserRepository,
    make_user,
)


@pytest.fixture
def repo():
    return InMemoryUserRepository()


@pytest.fixture
def hasher():
    return FakePasswordHasher()


@pytest.fixture
def tokens():
    return FakeTokenService()


@pytest.fixture
async def user(repo):
    user = make_user(email="ana@example.com", password="Secret123")
    await repo.add(user)
    return user


class TestRegisterUser:

    async def test_registers_with_hashed_password(self, repo, hasher):
        dto = RegisterUserDTO(email="New@Example.com", password="Secret123", full_name="New")

        result = await RegisterUserUseCase(repo, hasher).execute(dto)

        assert result.email == "new@example.com"
        stored = await repo.get_by_id(UserId.from_string(result.id))
        assert stored.hashed_password.value != "Secret123"
        assert hasher.verify("Secret123", stored.hashed_password)

    async def test_rejects_duplicate_email_case_insensitive(self, repo, hasher, user):
        dto = RegisterUserDTO(email="ANA@example.com", password="Secret123", full_name="Ana 2")

        with pytest.raises(UserAlreadyExistsError):
            await RegisterUserUseCase(repo, hasher).execute(dto)

    async def test_rejects_weak_password(self, repo, hasher):
        dto = RegisterUserDTO(email="new@example.com", password="weakpass", full_name="New")

        with pytest.raises(ValidationError):
            await RegisterUserUseCase(repo, hasher).execute(dto)
        assert repo.users == {}


class TestAuthenticateUser:

    async def test_returns_token_for_valid_credentials(self, repo, hasher, tokens, user):
        result = await AuthenticateUserUseCase(repo, hasher, tokens).execute(
            LoginDTO(email="ana@example.com", password="Secret123")
        )

        assert result.token_type == "bearer"
        assert tokens.decode_access_token(result.access_token).user_id == user.id
        assert result.user.id == str(user.id)

    @pytest.mark.parametrize(
        "email, password",
        [("ana@example.com", "Wrong1234"), ("nobody@example.com", "Secret123")],
    )
    async def test_same_error_for_wrong_password_and_unknown_email(
        self, repo, hasher, tokens, user, email, password
    ):
        with pytest.raises(InvalidCredentialsError):
            await AuthenticateUserUseCase(repo, hasher, tokens).execute(
                LoginDTO(email=email, password=password)
            )

    async def test_rejects_inactive_user(self, repo, hasher, tokens, user):
        user.deactivate()

        with pytest.raises(InactiveUserError):
            await AuthenticateUserUseCase(repo, hasher, tokens).execute(
                LoginDTO(email="ana@example.com", password="Secret123")
            )


class TestGetCurrentUser:

    async def test_resolves_user_from_token(self, repo, tokens, user):
        token = tokens.generate_access_token(user.id)

        result = await GetCurrentUserUseCase(repo, tokens).execute(token)

        assert result.id == str(user.id)

    async def test_rejects_invalid_token(self, repo, tokens):
        with pytest.raises(InvalidTokenError):
            await GetCurrentUserUseCase(repo, tokens).execute("garbage")

    async def test_rejects_token_of_deleted_user(self, repo, tokens):
        token = tokens.generate_access_token(UserId())

        with pytest.raises(UserNotFoundError):
            await GetCurrentUserUseCase(repo, tokens).execute(token)

    async def test_rejects_inactive_user(self, repo, tokens, user):
        user.deactivate()
        token = tokens.generate_access_token(user.id)

        with pytest.raises(InactiveUserError):
            await GetCurrentUserUseCase(repo, tokens).execute(token)


class TestChangePassword:

    async def test_changes_password(self, repo, hasher, user):
        await ChangePasswordUseCase(repo, hasher).execute(
            str(user.id),
            ChangePasswordDTO(current_password="Secret123", new_password="NewSecret456"),
        )

        assert hasher.verify("NewSecret456", user.hashed_password)
        assert not hasher.verify("Secret123", user.hashed_password)

    async def test_rejects_wrong_current_password(self, repo, hasher, user):
        with pytest.raises(IncorrectCurrentPasswordError):
            await ChangePasswordUseCase(repo, hasher).execute(
                str(user.id),
                ChangePasswordDTO(current_password="Wrong1234", new_password="NewSecret456"),
            )
        assert hasher.verify("Secret123", user.hashed_password)

    async def test_rejects_weak_new_password(self, repo, hasher, user):
        with pytest.raises(ValidationError):
            await ChangePasswordUseCase(repo, hasher).execute(
                str(user.id),
                ChangePasswordDTO(current_password="Secret123", new_password="onlyletters"),
            )

    async def test_accepts_legacy_short_current_password(self, repo, hasher):
        # Accounts created under the old 6-char rule must still be able to change it.
        legacy = make_user(email="old@example.com")
        legacy.change_password(HashedPassword("hashed:abc123"))  # FakePasswordHasher format
        await repo.add(legacy)

        await ChangePasswordUseCase(repo, hasher).execute(
            str(legacy.id),
            ChangePasswordDTO(current_password="abc123", new_password="NewSecret456"),
        )

        assert hasher.verify("NewSecret456", legacy.hashed_password)


class TestUpdatePreferences:

    async def test_update_unit_preference(self, repo, user):
        result = await UpdateUnitPreferenceUseCase(repo).execute(
            str(user.id), UpdateUnitPreferenceDTO(preferred_unit_system="us")
        )
        assert result.preferred_unit_system == "us"

    async def test_rejects_unknown_unit_system(self, repo, user):
        with pytest.raises(ValidationError):
            await UpdateUnitPreferenceUseCase(repo).execute(
                str(user.id), UpdateUnitPreferenceDTO(preferred_unit_system="kelvin")
            )

    async def test_update_language_returns_plain_code(self, repo, user):
        result = await UpdateLanguageUseCase(repo).execute(
            str(user.id), UpdateLanguageDTO(preferred_language="es")
        )
        assert result.preferred_language == "es"

    async def test_update_profile(self, repo, user):
        result = await UpdateProfileUseCase(repo).execute(
            str(user.id), UpdateUserDTO(full_name="Ana B", avatar_url=None)
        )
        assert result.full_name == "Ana B"

    async def test_unknown_user(self, repo):
        with pytest.raises(UserNotFoundError):
            await UpdateLanguageUseCase(repo).execute(
                str(UserId()), UpdateLanguageDTO(preferred_language="es")
            )


class TestActivation:

    async def test_deactivate_then_activate(self, repo, user):
        result = await DeactivateUserUseCase(repo).execute(str(user.id))
        assert result.is_active is False

        result = await ActivateUserUseCase(repo).execute(str(user.id))
        assert result.is_active is True

    async def test_invalid_id_is_validation_error(self, repo):
        with pytest.raises(ValidationError):
            await ActivateUserUseCase(repo).execute("not-a-uuid")

    async def test_unknown_user(self, repo):
        with pytest.raises(UserNotFoundError):
            await DeactivateUserUseCase(repo).execute(str(UserId()))
