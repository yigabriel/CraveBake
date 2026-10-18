from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.iam.domain.value_objects.plain_password import PlainPassword
from app.iam.domain.value_objects.user_id import UserId
from app.iam.infraestructure.security.bcrypt_password_hasher import BcryptPasswordHasher
from app.iam.infraestructure.security.jwt_token_service import JwtTokenService
from app.iam.infraestructure.security.login_rate_limiter import LoginRateLimiter
from app.shared.exceptions.domain_exceptions import TooManyRequestsError

SECRET = "unit-test-secret"


class TestBcryptPasswordHasher:

    def test_hash_and_verify(self):
        hasher = BcryptPasswordHasher()

        hashed = hasher.hash(PlainPassword("Secret123"))

        assert hashed.value != "Secret123"
        assert hasher.verify("Secret123", hashed)
        assert not hasher.verify("Secret124", hashed)

    def test_same_password_gets_different_salts(self):
        hasher = BcryptPasswordHasher()
        assert hasher.hash(PlainPassword("Secret123")) != hasher.hash(PlainPassword("Secret123"))


class TestJwtTokenService:

    def test_round_trip(self):
        service = JwtTokenService(SECRET, "HS256", expire_minutes=5)
        user_id = UserId()

        payload = service.decode_access_token(service.generate_access_token(user_id))

        assert payload.user_id == user_id

    def test_rejects_token_signed_with_other_secret(self):
        token = JwtTokenService("other-secret", "HS256", 5).generate_access_token(UserId())

        with pytest.raises(ValueError):
            JwtTokenService(SECRET, "HS256", 5).decode_access_token(token)

    def test_rejects_expired_token(self):
        expired = jwt.encode(
            {"sub": str(UserId()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
            SECRET,
            algorithm="HS256",
        )

        with pytest.raises(ValueError):
            JwtTokenService(SECRET, "HS256", 5).decode_access_token(expired)

    def test_rejects_token_without_subject(self):
        token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, SECRET, algorithm="HS256"
        )

        with pytest.raises(ValueError):
            JwtTokenService(SECRET, "HS256", 5).decode_access_token(token)


class FakeClock:

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class TestLoginRateLimiter:

    def _limiter(self, clock):
        return LoginRateLimiter(max_failures=3, window_seconds=60, clock=clock)

    def test_allows_until_limit_then_blocks(self):
        clock = FakeClock()
        limiter = self._limiter(clock)

        for _ in range(3):
            limiter.ensure_allowed("ip:ana")
            limiter.register_failure("ip:ana")

        with pytest.raises(TooManyRequestsError) as error:
            limiter.ensure_allowed("ip:ana")
        assert error.value.retry_after_seconds == 60

    def test_unblocks_when_window_passes(self):
        clock = FakeClock()
        limiter = self._limiter(clock)
        for _ in range(3):
            limiter.register_failure("ip:ana")

        clock.now += 30
        with pytest.raises(TooManyRequestsError) as error:
            limiter.ensure_allowed("ip:ana")
        assert error.value.retry_after_seconds == 30

        clock.now += 30
        limiter.ensure_allowed("ip:ana")

    def test_window_slides_per_failure(self):
        clock = FakeClock()
        limiter = self._limiter(clock)
        limiter.register_failure("ip:ana")
        clock.now += 40
        limiter.register_failure("ip:ana")
        limiter.register_failure("ip:ana")

        clock.now += 21  # first failure expired, two remain
        limiter.ensure_allowed("ip:ana")

    def test_reset_clears_failures(self):
        limiter = self._limiter(FakeClock())
        for _ in range(3):
            limiter.register_failure("ip:ana")

        limiter.reset("ip:ana")

        limiter.ensure_allowed("ip:ana")

    def test_keys_are_independent(self):
        limiter = self._limiter(FakeClock())
        for _ in range(3):
            limiter.register_failure("1.1.1.1:ana")

        limiter.ensure_allowed("2.2.2.2:ana")
        limiter.ensure_allowed("1.1.1.1:bob")
