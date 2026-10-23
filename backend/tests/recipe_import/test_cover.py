"""
The cover of an imported recipe: the video's thumbnail copied into our storage.
Nothing here talks to TikTok, Instagram or Supabase.
"""
from __future__ import annotations

import json

import httpx2
import pytest

from app.media.application.use_cases.store_image_use_case import StoreImageUseCase
from app.media.domain.services.image_uploader import ImageUploader
from app.media.domain.upload_policy import MAX_BYTES, ImagePurpose, ImageStorageUnavailableError, ImageTooLargeError, UnsupportedImageTypeError
from app.media.infrastructure.supabase_image_storage import SupabaseImageStorage
from app.recipe_import.application.dto.recipe_draft_dto import ImportRecipeDTO
from app.recipe_import.application.use_cases.import_recipe_from_video_use_case import ImportRecipeFromVideoUseCase
from app.recipe_import.domain.extracted_recipe import ExtractedIngredient, ExtractedRecipe
from app.recipe_import.domain.services.ports import CoverImageStore
from app.recipe_import.domain.video_text import VideoText
from app.recipe_import.infrastructure.thumbnail_cover_store import ThumbnailCoverStore, is_allowed_thumbnail_url
from tests.recipe_import.test_recipe_import import LONG_TEXT, TIKTOK, FakeCatalog, FakeExtractor, FakeSource

USER = "6f1c9d2e-0000-4000-8000-000000000001"
THUMB = "https://p16-sign-va.tiktokcdn.com/obj/tos/abc~tplv-photomode.jpeg?x-expires=1&x-signature=s"
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 1000


class TestAllowedHosts:

    @pytest.mark.parametrize(
        "url",
        [
            THUMB,
            "https://p16-sign.tiktokcdn-us.com/x.jpeg",
            "https://p19-pu-sign-useast8.tiktokcdn-us.com/x.webp",
            "https://scontent.cdninstagram.com/v/t51/x.jpg?stp=dst-jpg",
            "https://scontent-lim1-1.cdninstagram.com/v/x.jpg",
            "https://instagram.flim1-1.fna.fbcdn.net/v/x.jpg",
        ],
    )
    def test_the_platforms_image_cdns(self, url):
        assert is_allowed_thumbnail_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "http://p16-sign-va.tiktokcdn.com/x.jpeg",  # not https
            "https://localhost/x.jpg",
            "https://169.254.169.254/latest/meta-data",  # cloud metadata: the classic SSRF target
            "https://10.0.0.5/x.jpg",
            "https://tiktokcdn.com.evil.example/x.jpg",
            "https://eviltiktokcdn.com/x.jpg",  # a suffix match must be a whole label
            "https://user:pass@scontent.cdninstagram.com/x.jpg",
            "https://scontent.cdninstagram.com:8443/x.jpg",
            "javascript:alert(1)",
            "",
        ],
    )
    def test_anything_else_is_refused(self, url):
        assert not is_allowed_thumbnail_url(url)


class FakeMedia:
    def __init__(self, error: Exception | None = None) -> None:
        self.stored: list[tuple[str, str, int]] = []
        self.error = error

    async def store_recipe_photo(self, owner_user_id: str, content_type: str, data: bytes) -> str:
        if self.error:
            raise self.error
        self.stored.append((owner_user_id, content_type, len(data)))
        return f"https://storage.test/public/recipes/{owner_user_id}/copy.jpg"


def store(handler, media=None) -> tuple[ThumbnailCoverStore, FakeMedia]:
    media = media or FakeMedia()
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return ThumbnailCoverStore(media, client=client), media


class TestThumbnailCoverStore:

    async def test_copies_the_thumbnail_into_the_owners_folder(self):
        cover_store, media = store(lambda request: httpx2.Response(200, content=JPEG, headers={"content-type": "image/jpeg"}))

        url = await cover_store.store(THUMB, USER)

        assert url == f"https://storage.test/public/recipes/{USER}/copy.jpg"
        assert media.stored == [(USER, "image/jpeg", len(JPEG))]

    async def test_a_disallowed_host_is_never_requested(self):
        def handler(request):
            raise AssertionError("must not be requested")

        cover_store, media = store(handler)
        assert await cover_store.store("https://169.254.169.254/latest/meta-data", USER) is None
        assert media.stored == []

    async def test_redirects_are_not_followed(self):
        # An allowed CDN answering with a redirect must not lead the server somewhere else.
        calls = []

        def handler(request):
            calls.append(str(request.url))
            return httpx2.Response(302, headers={"location": "http://10.0.0.5/secret"})

        cover_store, media = store(handler)
        assert await cover_store.store(THUMB, USER) is None
        assert len(calls) == 1 and media.stored == []

    @pytest.mark.parametrize("content_type", ["image/heic", "image/svg+xml", "text/html", ""])
    async def test_only_types_a_person_could_upload(self, content_type):
        cover_store, media = store(lambda request: httpx2.Response(200, content=JPEG, headers={"content-type": content_type}))
        assert await cover_store.store(THUMB, USER) is None
        assert media.stored == []

    async def test_a_huge_answer_is_cut_off(self):
        cover_store, media = store(lambda request: httpx2.Response(200, content=b"0" * (MAX_BYTES + 10), headers={"content-type": "image/jpeg"}))
        assert await cover_store.store(THUMB, USER) is None
        assert media.stored == []

    async def test_an_expired_link_or_a_storage_problem_means_no_cover_not_a_failed_import(self):
        expired, _ = store(lambda request: httpx2.Response(403, text="expired"))
        assert await expired.store(THUMB, USER) is None

        broken, _ = store(lambda request: httpx2.Response(200, content=JPEG, headers={"content-type": "image/jpeg"}), media=FakeMedia(ImageStorageUnavailableError()))
        assert await broken.store(THUMB, USER) is None

        def down(request):
            raise httpx2.ConnectError("down")

        unreachable, _ = store(down)
        assert await unreachable.store(THUMB, USER) is None


class FakeCovers(CoverImageStore):
    def __init__(self, answer: str | None = "https://storage.test/public/cover.jpg") -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    async def store(self, image_url, owner_user_id):
        self.calls.append((image_url, owner_user_id))
        return self.answer


def importer(recipe: ExtractedRecipe, thumbnail: str | None = THUMB, covers: FakeCovers | None = None):
    text = VideoText(title="Brownies", description=LONG_TEXT, transcript=None, author="@baker", thumbnail_url=thumbnail)
    covers = covers if covers is not None else FakeCovers()
    return ImportRecipeFromVideoUseCase(FakeSource(text), FakeExtractor(recipe), FakeCatalog(), covers), covers


RECIPE = ExtractedRecipe(is_recipe=True, ingredients=[ExtractedIngredient("a")])


class TestCoverInTheImport:

    async def test_the_draft_carries_our_copy_of_the_thumbnail(self):
        use_case, covers = importer(RECIPE)
        draft = await use_case.execute(ImportRecipeDTO(TIKTOK, user_id=USER))

        assert draft.cover_url == "https://storage.test/public/cover.jpg"
        assert covers.calls == [(THUMB, USER)]

    async def test_no_copy_is_made_for_a_video_that_is_not_a_recipe(self):
        from app.recipe_import.domain.video_text import NotARecipeError

        use_case, covers = importer(ExtractedRecipe(is_recipe=False))
        with pytest.raises(NotARecipeError):
            await use_case.execute(ImportRecipeDTO(TIKTOK, user_id=USER))
        assert covers.calls == []

    async def test_no_thumbnail_or_no_copy_means_no_cover(self):
        without, covers = importer(RECIPE, thumbnail=None)
        assert (await without.execute(ImportRecipeDTO(TIKTOK, user_id=USER))).cover_url is None
        assert covers.calls == []

        failed, _ = importer(RECIPE, covers=FakeCovers(answer=None))
        assert (await failed.execute(ImportRecipeDTO(TIKTOK, user_id=USER))).cover_url is None

    async def test_without_a_cover_store_the_import_still_works(self):
        use_case = ImportRecipeFromVideoUseCase(
            FakeSource(VideoText("Brownies", LONG_TEXT, None, None, THUMB)), FakeExtractor(RECIPE), FakeCatalog(), None
        )
        assert (await use_case.execute(ImportRecipeDTO(TIKTOK, user_id=USER))).cover_url is None


class FakeUploader(ImageUploader):
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, int]] = []

    async def upload(self, path, data, content_type):
        self.uploads.append((path, content_type, len(data)))
        return f"https://storage.test/public/{path}"


class TestStoreImage:

    async def test_same_rules_as_a_browser_upload(self):
        uploader = FakeUploader()
        url = await StoreImageUseCase(uploader).execute(USER, ImagePurpose.RECIPE, "image/webp", b"x" * 10)

        path = uploader.uploads[0][0]
        assert path.startswith(f"recipes/{USER}/") and path.endswith(".webp") and url.endswith(path)

    async def test_refuses_what_a_browser_could_not_upload_either(self):
        with pytest.raises(UnsupportedImageTypeError):
            await StoreImageUseCase(FakeUploader()).execute(USER, ImagePurpose.RECIPE, "image/gif", b"x")
        with pytest.raises(ImageTooLargeError):
            await StoreImageUseCase(FakeUploader()).execute(USER, ImagePurpose.RECIPE, "image/jpeg", b"x" * (MAX_BYTES + 1))


class TestSupabaseServerUpload:

    async def test_uploads_with_the_secret_key_and_returns_the_public_url(self):
        seen = {}

        def handler(request):
            seen.update(method=request.method, url=str(request.url), headers=dict(request.headers), size=len(request.read()))
            return httpx2.Response(200, json={"Key": "recipe-photos/recipes/u/a.jpg"})

        storage = SupabaseImageStorage(
            "https://abcd.supabase.co", "sb_secret_test", "recipe-photos", client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
        )
        url = await storage.upload("recipes/u/a.jpg", JPEG, "image/jpeg")

        assert url == "https://abcd.supabase.co/storage/v1/object/public/recipe-photos/recipes/u/a.jpg"
        assert (seen["method"], seen["url"], seen["size"]) == ("POST", "https://abcd.supabase.co/storage/v1/object/recipe-photos/recipes/u/a.jpg", len(JPEG))
        assert (seen["headers"]["apikey"], seen["headers"]["content-type"], seen["headers"]["x-upsert"]) == ("sb_secret_test", "image/jpeg", "false")

    @pytest.mark.parametrize("status", [400, 401, 409, 500])
    async def test_refusals_become_unavailable(self, status):
        storage = SupabaseImageStorage(
            "https://abcd.supabase.co", "sb_secret_test", "recipe-photos",
            client=httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: httpx2.Response(status, json={"message": "nope"}))),
        )
        with pytest.raises(ImageStorageUnavailableError):
            await storage.upload("recipes/u/a.jpg", JPEG, "image/jpeg")


class TestSupadataThumbnail:

    async def test_the_thumbnail_comes_with_the_metadata(self):
        from app.recipe_import.domain.source_url import SourceUrl, VideoPlatform
        from app.recipe_import.infrastructure.supadata_video_text_source import SupadataVideoTextSource

        def handler(request):
            if request.url.path.endswith("/metadata"):
                return httpx2.Response(200, json={"title": "t", "description": LONG_TEXT, "media": {"duration": 30, "thumbnailUrl": THUMB}})
            return httpx2.Response(206, json={"error": "transcript-unavailable"})

        source = SupadataVideoTextSource("k", client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)), min_interval=0)
        text = await source.fetch(SourceUrl(VideoPlatform.TIKTOK, TIKTOK))
        assert text.thumbnail_url == THUMB

    def test_no_media_no_thumbnail(self):
        assert VideoText.clean("t", None, None, None).thumbnail_url is None


def test_the_response_schema_documents_the_cover():
    from app.recipe_import.presentation.http.schemas.recipe_import_schemas import RecipeDraftResponse

    assert "cover_url" in json.dumps(RecipeDraftResponse.model_json_schema())
