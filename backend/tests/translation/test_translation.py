"""
Suggested translations of catalog names: the use case with a fake translator,
the Google adapter against a mocked network, the rate limiter and the HTTP
endpoint. Nothing here talks to Google.
"""
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.iam.presentation.http.dependencies import get_password_hasher, get_user_repository
from app.main import app
from app.shared.exceptions.domain_exceptions import TooManyRequestsError, ValidationError
from app.translation.application.dto.translation_dto import SuggestTranslationsDTO
from app.translation.application.use_cases.suggest_translations_use_case import SuggestTranslationsUseCase
from app.translation.domain.exceptions import TranslationUnavailableError
from app.translation.domain.services.text_translator import TextTranslator
from app.translation.infrastructure.azure_translator import AzureTranslator
from app.translation.infrastructure.google_cloud_translator import GoogleCloudTranslator
from app.shared.presentation.request_rate_limiter import RequestRateLimiter
from app.translation.presentation.http.dependencies import get_translation_rate_limiter, get_translator
from tests.iam.fakes import FakePasswordHasher, InMemoryUserRepository


class FakeTranslator(TextTranslator):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def translate(self, text: str, source: str, target: str) -> str:
        self.calls.append((text, source, target))
        return f"  {text} [{target}] "


class TestSuggestTranslations:

    async def test_suggests_every_other_language_and_nothing_else(self):
        translator = FakeTranslator()

        result = await SuggestTranslationsUseCase(translator).execute(SuggestTranslationsDTO(" Pistacho ", "es"))

        assert result == {"en": "Pistacho [en]"}
        assert translator.calls == [("Pistacho", "es", "en")]

    async def test_goes_the_other_way_too(self):
        result = await SuggestTranslationsUseCase(FakeTranslator()).execute(SuggestTranslationsDTO("Pistachio", "en"))
        assert result == {"es": "Pistachio [es]"}

    @pytest.mark.parametrize("text, source", [("   ", "es"), ("Pistacho", "fr")])
    async def test_rejects_blank_text_and_unknown_languages(self, text, source):
        with pytest.raises(ValidationError):
            await SuggestTranslationsUseCase(FakeTranslator()).execute(SuggestTranslationsDTO(text, source))


def _google(handler):
    return GoogleCloudTranslator("test-key", client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


class TestGoogleAdapter:

    async def test_sends_the_key_in_a_header_and_reads_the_translation(self):
        seen = {}

        def handler(request):
            seen["url"], seen["key"], seen["body"] = str(request.url), request.headers.get("x-goog-api-key"), request.read()
            return httpx2.Response(200, json={"data": {"translations": [{"translatedText": "Pistachio"}]}})

        assert await _google(handler).translate("Pistacho", "es", "en") == "Pistachio"
        assert seen["key"] == "test-key"
        assert "test-key" not in seen["url"]  # never in the URL: it would reach access logs
        assert b'"format":"text"' in seen["body"].replace(b" ", b"")

    @pytest.mark.parametrize("status", [400, 403, 429, 500])
    async def test_google_refusals_become_unavailable(self, status):
        with pytest.raises(TranslationUnavailableError):
            await _google(lambda request: httpx2.Response(status, json={"error": {"message": "nope"}})).translate("a", "es", "en")

    async def test_network_errors_become_unavailable(self):
        def handler(request):
            raise httpx2.ConnectError("down")

        with pytest.raises(TranslationUnavailableError):
            await _google(handler).translate("a", "es", "en")

    @pytest.mark.parametrize("body", [{}, {"data": {}}, {"data": {"translations": []}}])
    async def test_unexpected_answers_become_unavailable(self, body):
        with pytest.raises(TranslationUnavailableError):
            await _google(lambda request: httpx2.Response(200, json=body)).translate("a", "es", "en")


def _azure(handler):
    return AzureTranslator("test-key", "brazilsouth", client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


class TestAzureAdapter:

    async def test_sends_key_and_region_in_headers_and_reads_the_translation(self):
        seen = {}

        def handler(request):
            seen["request"] = request
            return httpx2.Response(200, json=[{"translations": [{"text": "Pistachio", "to": "en"}]}])

        assert await _azure(handler).translate("Pistacho", "es", "en") == "Pistachio"
        request = seen["request"]
        assert request.headers.get("ocp-apim-subscription-key") == "test-key"
        assert request.headers.get("ocp-apim-subscription-region") == "brazilsouth"
        assert "test-key" not in str(request.url)  # never in the URL: it would reach access logs
        assert request.url.path == "/translate"
        assert dict(request.url.params) == {"api-version": "3.0", "from": "es", "to": "en", "textType": "plain"}
        assert request.read().replace(b" ", b"") == b'[{"Text":"Pistacho"}]'

    @pytest.mark.parametrize("status", [400, 401, 403, 429, 500])
    async def test_azure_refusals_become_unavailable(self, status):
        with pytest.raises(TranslationUnavailableError):
            await _azure(lambda request: httpx2.Response(status, json={"error": {"code": 401000}})).translate("a", "es", "en")

    async def test_network_errors_become_unavailable(self):
        def handler(request):
            raise httpx2.ConnectError("down")

        with pytest.raises(TranslationUnavailableError):
            await _azure(handler).translate("a", "es", "en")

    @pytest.mark.parametrize("body", [{}, [], [{}], [{"translations": []}]])
    async def test_unexpected_answers_become_unavailable(self, body):
        with pytest.raises(TranslationUnavailableError):
            await _azure(lambda request: httpx2.Response(200, json=body)).translate("a", "es", "en")


class TestTranslatorWiring:

    @pytest.fixture
    def settings(self, monkeypatch):
        from app.shared.config.settings import get_settings
        settings = get_settings().model_copy()
        monkeypatch.setattr("app.translation.presentation.http.dependencies.get_settings", lambda: settings)
        return settings

    def test_azure_is_the_default_and_needs_key_and_region(self, settings):
        settings.translation_provider, settings.azure_translator_key, settings.azure_translator_region = "azure", "k", None
        with pytest.raises(TranslationUnavailableError):
            get_translator()
        settings.azure_translator_region = "brazilsouth"
        assert isinstance(get_translator(), AzureTranslator)

    def test_google_is_a_switch_away(self, settings):
        settings.translation_provider, settings.google_translate_api_key = "google", "k"
        assert isinstance(get_translator(), GoogleCloudTranslator)


class TestRateLimiter:

    def test_blocks_the_n_plus_first_request_until_the_window_passes(self):
        now = [0.0]
        limiter = RequestRateLimiter(2, 60, clock=lambda: now[0])

        limiter.hit("ana")
        limiter.hit("ana")
        with pytest.raises(TooManyRequestsError) as blocked:
            limiter.hit("ana")
        assert blocked.value.retry_after_seconds == 60

        limiter.hit("luis")  # another user is not affected
        now[0] = 61
        limiter.hit("ana")


class TestEndpoint:

    @pytest.fixture
    def client(self):
        users = InMemoryUserRepository()
        app.dependency_overrides[get_user_repository] = lambda: users
        app.dependency_overrides[get_password_hasher] = FakePasswordHasher
        app.dependency_overrides[get_translator] = FakeTranslator
        limiter = RequestRateLimiter(3, 60)
        app.dependency_overrides[get_translation_rate_limiter] = lambda: limiter
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def _headers(self, client):
        client.post("/v1/auth/register", json={"email": "baker@example.com", "password": "Password1", "full_name": "Baker"})
        token = client.post("/v1/auth/login", data={"username": "baker@example.com", "password": "Password1"}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_a_signed_in_user_gets_suggestions(self, client):
        response = client.post("/v1/translations", json={"text": "Pistacho", "source": "es"}, headers=self._headers(client))
        assert (response.status_code, response.json()) == (200, {"translations": {"en": "Pistacho [en]"}})

    def test_requires_sign_in(self, client):
        assert client.post("/v1/translations", json={"text": "Pistacho", "source": "es"}).status_code == 401

    @pytest.mark.parametrize("body", [{"text": "", "source": "es"}, {"text": "x" * 256, "source": "es"}, {"text": "a", "source": "fr"}])
    def test_rejects_bad_requests(self, client, body):
        assert client.post("/v1/translations", json=body, headers=self._headers(client)).status_code == 422

    def test_without_a_key_configured_answers_503(self, client):
        headers = self._headers(client)

        def unconfigured():
            raise TranslationUnavailableError()

        app.dependency_overrides[get_translator] = unconfigured
        response = client.post("/v1/translations", json={"text": "Pistacho", "source": "es"}, headers=headers)
        assert (response.status_code, response.json()["code"]) == (503, "service_unavailable")

    def test_too_many_requests_answer_429_with_retry_after(self, client):
        headers = self._headers(client)
        for _ in range(3):
            assert client.post("/v1/translations", json={"text": "a", "source": "es"}, headers=headers).status_code == 200

        blocked = client.post("/v1/translations", json={"text": "a", "source": "es"}, headers=headers)

        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) >= 1
