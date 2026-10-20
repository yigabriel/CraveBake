"""
Photo uploads: the policy, the use case with a fake storage, the Supabase
adapter against a mocked network, and the HTTP endpoint. Nothing here talks
to the real Supabase.
"""
import re

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.iam.presentation.http.dependencies import get_password_hasher, get_user_repository
from app.main import app
from app.media.application.dto.image_upload_dto import RequestImageUploadDTO
from app.media.application.use_cases.request_image_upload_use_case import RequestImageUploadUseCase
from app.media.domain.services.image_storage import ImageStorage, SignedUpload
from app.media.domain.upload_policy import (
    MAX_BYTES,
    ImagePurpose,
    ImageStorageUnavailableError,
    UnsupportedImageTypeError,
    object_path,
)
from app.media.infrastructure.supabase_image_storage import SupabaseImageStorage
from app.media.presentation.http.dependencies import get_image_storage
from tests.iam.fakes import FakePasswordHasher, InMemoryUserRepository

USER = "6f1c9d2e-0000-4000-8000-000000000001"


class FakeStorage(ImageStorage):
    def __init__(self) -> None:
        self.paths: list[str] = []

    async def create_signed_upload(self, path: str) -> SignedUpload:
        self.paths.append(path)
        return SignedUpload(upload_url=f"https://storage.test/sign/{path}?token=t", public_url=f"https://storage.test/public/{path}")


class TestUploadPolicy:

    @pytest.mark.parametrize(
        "purpose, content_type, pattern",
        [
            (ImagePurpose.RECIPE, "image/webp", rf"^recipes/{USER}/[0-9a-f]{{32}}\.webp$"),
            (ImagePurpose.AVATAR, "image/jpeg", rf"^avatars/{USER}/[0-9a-f]{{32}}\.jpg$"),
            (ImagePurpose.RECIPE, "image/png", rf"^recipes/{USER}/[0-9a-f]{{32}}\.png$"),
        ],
    )
    def test_paths_are_grouped_by_purpose_and_owner(self, purpose, content_type, pattern):
        assert re.match(pattern, object_path(purpose, USER, content_type))

    def test_every_upload_gets_its_own_path(self):
        assert object_path(ImagePurpose.RECIPE, USER, "image/webp") != object_path(ImagePurpose.RECIPE, USER, "image/webp")

    @pytest.mark.parametrize("content_type", ["image/gif", "image/svg+xml", "application/pdf", ""])
    def test_rejects_other_types(self, content_type):
        with pytest.raises(UnsupportedImageTypeError):
            object_path(ImagePurpose.RECIPE, USER, content_type)


class TestRequestImageUpload:

    async def test_returns_where_to_upload_and_where_it_will_live(self):
        storage = FakeStorage()
        upload = await RequestImageUploadUseCase(storage).execute(RequestImageUploadDTO(USER, "avatar", "image/webp"))

        assert storage.paths[0].startswith(f"avatars/{USER}/")
        assert upload.upload_url.startswith("https://storage.test/sign/avatars/")
        assert upload.public_url.endswith(storage.paths[0])
        assert (upload.content_type, upload.max_bytes) == ("image/webp", MAX_BYTES)


def _adapter(handler, url="https://abcd.supabase.co/rest/v1/"):
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return SupabaseImageStorage(url, "sb_secret_test", "recipe-photos", client=client)


class TestSupabaseAdapter:

    async def test_signs_with_the_secret_key_and_builds_both_urls(self):
        seen = {}

        def handler(request):
            seen["url"], seen["apikey"] = str(request.url), request.headers.get("apikey")
            return httpx2.Response(200, json={"url": "/object/upload/sign/recipe-photos/recipes/u/a.webp?token=xyz"})

        # The dashboard's ".../rest/v1/" form of the project URL works too.
        signed = await _adapter(handler).create_signed_upload("recipes/u/a.webp")

        assert seen == {"url": "https://abcd.supabase.co/storage/v1/object/upload/sign/recipe-photos/recipes/u/a.webp", "apikey": "sb_secret_test"}
        assert signed.upload_url == "https://abcd.supabase.co/storage/v1/object/upload/sign/recipe-photos/recipes/u/a.webp?token=xyz"
        assert signed.public_url == "https://abcd.supabase.co/storage/v1/object/public/recipe-photos/recipes/u/a.webp"

    @pytest.mark.parametrize("status", [400, 401, 404, 500])
    async def test_storage_refusals_become_unavailable(self, status):
        with pytest.raises(ImageStorageUnavailableError):
            await _adapter(lambda request: httpx2.Response(status, json={"message": "nope"})).create_signed_upload("x.webp")

    async def test_network_errors_become_unavailable(self):
        def handler(request):
            raise httpx2.ConnectError("down")

        with pytest.raises(ImageStorageUnavailableError):
            await _adapter(handler).create_signed_upload("x.webp")


class TestUploadEndpoint:

    @pytest.fixture
    def client(self):
        app.dependency_overrides[get_user_repository] = InMemoryUserRepository
        app.dependency_overrides[get_password_hasher] = FakePasswordHasher
        app.dependency_overrides[get_image_storage] = FakeStorage
        users = InMemoryUserRepository()
        app.dependency_overrides[get_user_repository] = lambda: users
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def _token(self, client):
        client.post("/v1/auth/register", json={"email": "baker@example.com", "password": "Password1", "full_name": "Baker"})
        token = client.post("/v1/auth/login", data={"username": "baker@example.com", "password": "Password1"}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_signed_in_user_gets_an_upload(self, client):
        response = client.post("/v1/media/uploads", json={"purpose": "recipe", "content_type": "image/webp"}, headers=self._token(client))
        assert response.status_code == 201
        body = response.json()
        assert body["upload_url"].startswith("https://storage.test/sign/recipes/")
        assert body["max_bytes"] == MAX_BYTES

    def test_requires_sign_in(self, client):
        assert client.post("/v1/media/uploads", json={"purpose": "recipe", "content_type": "image/webp"}).status_code == 401

    @pytest.mark.parametrize("body", [{"purpose": "recipe", "content_type": "image/gif"}, {"purpose": "banner", "content_type": "image/webp"}])
    def test_rejects_bad_requests(self, client, body):
        assert client.post("/v1/media/uploads", json=body, headers=self._token(client)).status_code == 422

    def test_without_storage_configured_answers_503(self, client):
        headers = self._token(client)

        def unconfigured():
            raise ImageStorageUnavailableError()

        app.dependency_overrides[get_image_storage] = unconfigured
        response = client.post("/v1/media/uploads", json={"purpose": "avatar", "content_type": "image/webp"}, headers=headers)
        assert (response.status_code, response.json()["code"]) == (503, "service_unavailable")
