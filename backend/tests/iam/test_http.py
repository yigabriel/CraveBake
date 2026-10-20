"""
End-to-end HTTP tests for IAM, CORS and error handling.

The real app is used with the repository, hasher and rate limiter swapped
through `dependency_overrides`, so requests never reach the database.
"""
import pytest
from fastapi.testclient import TestClient

from app.iam.infraestructure.security.login_rate_limiter import LoginRateLimiter
from app.iam.presentation.http.dependencies import (
    get_login_rate_limiter,
    get_password_hasher,
    get_user_repository,
)
from app.main import app
from app.shared.config.settings import get_settings
from tests.iam.fakes import FakePasswordHasher, InMemoryUserRepository

PASSWORD = "Secret123"


@pytest.fixture
def repo():
    return InMemoryUserRepository()


@pytest.fixture
def client(repo):
    limiter = LoginRateLimiter(max_failures=3, window_seconds=60)
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_password_hasher] = FakePasswordHasher
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(client, email="ana@example.com", password=PASSWORD):
    return client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Ana"},
    )


def login(client, email="ana@example.com", password=PASSWORD):
    return client.post("/v1/auth/login", data={"username": email, "password": password})


def auth_headers(client, email="ana@example.com"):
    token = login(client, email).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuth:

    def test_register_then_login(self, client):
        response = register(client)
        assert response.status_code == 201
        assert response.json()["email"] == "ana@example.com"
        assert "hashed_password" not in response.json()

        response = login(client)
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.parametrize(
        "body_language, accept_language, expected",
        [
            ("es", "en-US,en;q=0.9", "es"),  # explicit choice wins
            (None, "es-AR,es;q=0.9,en;q=0.8", "es"),  # else the browser's first supported language
            (None, "fr-FR,fr;q=0.9,en;q=0.5", "en"),
            (None, None, "en"),  # else the default
        ],
    )
    def test_register_speaks_the_language_of_the_sign_up(self, client, body_language, accept_language, expected):
        body = {"email": "lang@example.com", "password": "Password1", "full_name": "Lang"}
        if body_language:
            body["preferred_language"] = body_language
        headers = {"Accept-Language": accept_language} if accept_language else {}
        response = client.post("/v1/auth/register", json=body, headers=headers)
        assert (response.status_code, response.json()["preferred_language"]) == (201, expected)

    def test_register_rejects_unknown_language(self, client):
        body = {"email": "fr@example.com", "password": "Password1", "full_name": "Fr", "preferred_language": "fr"}
        assert client.post("/v1/auth/register", json=body).status_code == 422

    def test_register_duplicate_is_409(self, client):
        register(client)
        response = register(client, email="ANA@example.com")
        assert response.status_code == 409
        assert response.json()["code"] == "conflict"

    def test_register_short_password_is_422(self, client):
        response = register(client, password="Ab1")
        assert response.status_code == 422
        assert response.json()["errors"][0]["field"] == "body.password"

    def test_register_weak_password_is_400(self, client):
        response = register(client, password="onlyletters")
        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"

    def test_wrong_password_is_401(self, client):
        register(client)
        response = login(client, password="Wrong1234")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


class TestLoginRateLimit:

    def test_locks_out_after_repeated_failures(self, client):
        register(client)
        for _ in range(3):
            assert login(client, password="Wrong1234").status_code == 401

        response = login(client)  # even the right password is blocked now

        assert response.status_code == 429
        assert response.json()["code"] == "too_many_requests"
        assert int(response.headers["Retry-After"]) > 0

    def test_successful_login_resets_counter(self, client):
        register(client)
        for _ in range(2):
            login(client, password="Wrong1234")

        assert login(client).status_code == 200

        for _ in range(2):
            assert login(client, password="Wrong1234").status_code == 401
        assert login(client).status_code == 200

    def test_lockout_is_per_email(self, client):
        register(client)
        register(client, email="bob@example.com")
        for _ in range(3):
            login(client, password="Wrong1234")

        assert login(client, email="bob@example.com").status_code == 200

    def test_email_case_does_not_bypass_lockout(self, client):
        register(client)
        for email in ["ana@example.com", "ANA@example.com", "Ana@Example.com"]:
            login(client, email=email, password="Wrong1234")

        assert login(client).status_code == 429


class TestMe:

    def test_get_profile(self, client):
        register(client)
        response = client.get("/v1/users/me", headers=auth_headers(client))
        assert response.status_code == 200
        assert response.json()["email"] == "ana@example.com"

    def test_requires_token(self, client):
        assert client.get("/v1/users/me").status_code == 401

    def test_rejects_garbage_token(self, client):
        response = client.get("/v1/users/me", headers={"Authorization": "Bearer nope"})
        assert response.status_code == 401

    def test_inactive_user_cannot_edit_profile(self, client, repo):
        register(client)
        headers = auth_headers(client)
        next(iter(repo.users.values())).deactivate()

        response = client.patch("/v1/users/me/language", json={"preferred_language": "es"}, headers=headers)

        assert response.status_code == 401
        assert response.json()["detail"] == "This user account is inactive"

    def test_update_language(self, client):
        register(client)
        response = client.patch(
            "/v1/users/me/language", json={"preferred_language": "es"}, headers=auth_headers(client)
        )
        assert response.status_code == 200
        assert response.json()["preferred_language"] == "es"

    def test_unknown_language_is_400_not_500(self, client):
        register(client)
        response = client.patch(
            "/v1/users/me/language", json={"preferred_language": "xx"}, headers=auth_headers(client)
        )
        assert response.status_code == 400

    def test_unknown_unit_system_is_400_not_500(self, client):
        register(client)
        response = client.patch(
            "/v1/users/me/unit-preference",
            json={"preferred_unit_system": "kelvin"},
            headers=auth_headers(client),
        )
        assert response.status_code == 400

    def test_change_password(self, client):
        register(client)
        headers = auth_headers(client)

        response = client.patch(
            "/v1/users/me/change-password",
            json={"current_password": PASSWORD, "new_password": "NewSecret456"},
            headers=headers,
        )

        assert response.status_code == 200
        assert login(client, password="NewSecret456").status_code == 200

    def test_change_password_wrong_current_is_400(self, client):
        register(client)
        response = client.patch(
            "/v1/users/me/change-password",
            json={"current_password": "Wrong1234", "new_password": "NewSecret456"},
            headers=auth_headers(client),
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Current password is incorrect"


class TestRemovedAdminRoutes:

    @pytest.mark.parametrize("action", ["activate", "deactivate"])
    def test_activation_routes_are_not_exposed(self, client, repo, action):
        register(client)
        user_id = str(next(iter(repo.users)))

        response = client.patch(f"/v1/users/{user_id}/{action}")

        assert response.status_code in (404, 405)
        assert next(iter(repo.users.values())).is_active is True


class TestCors:

    def test_allowed_origin_preflight(self, client):
        # Whatever the local .env configures, its first origin must be accepted.
        origin = get_settings().cors_allowed_origins[0]

        response = client.options(
            "/v1/auth/login",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin

    def test_unknown_origin_is_not_allowed(self, client):
        response = client.options(
            "/v1/auth/login",
            headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
        )
        assert "access-control-allow-origin" not in response.headers
