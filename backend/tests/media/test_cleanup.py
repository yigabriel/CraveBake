"""
Storage clean-up: the sweep use case with fakes, the Supabase listing/deleting against a
mocked network, and a guard that every column storing an image URL is looked at.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx2
import pytest

from app.media.application.use_cases.clean_orphaned_images_use_case import (
    BATCH,
    CleanOrphanedImagesUseCase,
    CleanupRefusedError,
)
from app.media.domain.services.image_references import ImageReferences
from app.media.domain.services.stored_images import StoredImage, StoredImages
from app.media.domain.upload_policy import ImageStorageUnavailableError
from app.media.infrastructure.sql_image_references import COLUMNS
from app.media.infrastructure.supabase_image_storage import LIST_PAGE, SupabaseImageStorage

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
PUBLIC = "https://abcd.supabase.co/storage/v1/object/public/recipe-photos/"
DAY = timedelta(hours=24)


class FakeStorage(StoredImages):
    def __init__(self, images: list[StoredImage]) -> None:
        self.images = images
        self.deleted: list[list[str]] = []

    async def list_all(self) -> list[StoredImage]:
        return self.images

    async def delete(self, paths: list[str]) -> None:
        self.deleted.append(paths)

    def path_of(self, url: str) -> str | None:
        return url[len(PUBLIC):] if url.startswith(PUBLIC) else None


class FakeReferences(ImageReferences):
    def __init__(self, *urls: str) -> None:
        self._urls = set(urls)

    async def urls(self) -> set[str]:
        return self._urls


def old(path: str) -> StoredImage:
    return StoredImage(path, NOW - timedelta(days=3))


def sweep(storage, references):
    return CleanOrphanedImagesUseCase(storage, references, now=lambda: NOW)


class TestSweep:

    async def test_reports_only_what_nothing_references(self):
        storage = FakeStorage([old("recipes/u/a.webp"), old("recipes/u/b.webp"), old("avatars/u/c.webp")])
        report = await sweep(storage, FakeReferences(PUBLIC + "recipes/u/a.webp", PUBLIC + "avatars/u/c.webp")).execute(DAY)

        assert report.orphans == ["recipes/u/b.webp"]
        assert (report.stored, report.referenced, report.deleted) == (3, 2, 0)
        assert storage.deleted == []  # a dry run deletes nothing

    async def test_a_url_that_two_places_share_keeps_the_file(self):
        # A personalization and its original both point to the same file: removing one photo must not free it.
        storage = FakeStorage([old("recipes/u/shared.webp")])
        report = await sweep(storage, FakeReferences(PUBLIC + "recipes/u/shared.webp", "https://other.example/x.jpg")).execute(DAY)

        assert report.orphans == []

    async def test_recent_files_are_left_alone(self):
        fresh = StoredImage("recipes/u/new.webp", NOW - timedelta(hours=1))
        unknown_age = StoredImage("recipes/u/unknown.webp", None)
        storage = FakeStorage([fresh, unknown_age, old("recipes/u/kept.webp"), old("recipes/u/gone.webp")])
        report = await sweep(storage, FakeReferences(PUBLIC + "recipes/u/kept.webp")).execute(DAY)

        assert (report.orphans, report.too_recent) == (["recipes/u/gone.webp"], 2)

    async def test_apply_deletes_in_batches(self):
        paths = [f"recipes/u/{n}.webp" for n in range(BATCH + 5)]
        storage = FakeStorage([old(path) for path in paths] + [old("recipes/u/kept.webp")])
        report = await sweep(storage, FakeReferences(PUBLIC + "recipes/u/kept.webp")).execute(DAY, apply=True)

        assert [len(batch) for batch in storage.deleted] == [BATCH, 5]
        assert (report.deleted, sorted(sum(storage.deleted, []))) == (BATCH + 5, sorted(paths))

    async def test_refuses_when_nothing_is_referenced(self):
        # Wrong database, or the references were not read: deleting would wipe every photo.
        storage = FakeStorage([old("recipes/u/a.webp")])
        with pytest.raises(CleanupRefusedError):
            await sweep(storage, FakeReferences()).execute(DAY, apply=True)
        assert storage.deleted == []

    async def test_force_overrides_the_refusal_and_an_empty_bucket_is_fine(self):
        storage = FakeStorage([old("recipes/u/a.webp")])
        report = await sweep(storage, FakeReferences()).execute(DAY, apply=True, force=True)
        assert report.deleted == 1
        assert (await sweep(FakeStorage([]), FakeReferences()).execute(DAY, apply=True)).deleted == 0


def adapter(handler) -> SupabaseImageStorage:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return SupabaseImageStorage("https://abcd.supabase.co/rest/v1/", "sb_secret_test", "recipe-photos", client=client)


class TestSupabaseListing:

    async def test_walks_folders_and_pages(self):
        calls = []

        def handler(request):
            body = request.read().decode()
            calls.append((str(request.url), body))
            import json

            sent = json.loads(body)
            file = lambda name, when="2026-10-18T10:00:00.000000+00:00": {"name": name, "id": f"id-{name}", "created_at": when}
            folder = lambda name: {"name": name, "id": None}
            listing = {
                ("", 0): [folder("recipes"), folder("avatars")],
                ("recipes/", 0): [folder("u1")],
                ("avatars/", 0): [file("a.webp")],
                ("recipes/u1/", 0): [file(f"{n}.webp") for n in range(LIST_PAGE)],  # a full page: ask for the next
                ("recipes/u1/", LIST_PAGE): [file("last.webp", None)],
            }
            return httpx2.Response(200, json=listing[(sent["prefix"], sent["offset"])])

        images = await adapter(handler).list_all()

        assert len(images) == 1 + LIST_PAGE + 1
        assert {"avatars/a.webp", "recipes/u1/0.webp", "recipes/u1/last.webp"} <= {image.path for image in images}
        assert next(i for i in images if i.path == "recipes/u1/last.webp").created_at is None
        assert next(i for i in images if i.path == "avatars/a.webp").created_at == datetime(2026, 10, 18, 10, tzinfo=timezone.utc)
        assert calls[0][0] == "https://abcd.supabase.co/storage/v1/object/list/recipe-photos"

    async def test_delete_sends_the_paths(self):
        seen = {}

        def handler(request):
            import json

            seen.update(method=request.method, url=str(request.url), body=json.loads(request.read()), apikey=request.headers["apikey"])
            return httpx2.Response(200, json=[])

        await adapter(handler).delete(["recipes/u/a.webp"])

        assert seen == {
            "method": "DELETE",
            "url": "https://abcd.supabase.co/storage/v1/object/recipe-photos",
            "body": {"prefixes": ["recipes/u/a.webp"]},
            "apikey": "sb_secret_test",
        }

    async def test_delete_nothing_makes_no_request(self):
        def handler(request):
            raise AssertionError("no request expected")

        await adapter(handler).delete([])

    @pytest.mark.parametrize("action", ["list_all", "delete"])
    async def test_storage_errors_become_unavailable(self, action):
        storage = adapter(lambda request: httpx2.Response(500, json={"message": "boom"}))
        with pytest.raises(ImageStorageUnavailableError):
            await (storage.list_all() if action == "list_all" else storage.delete(["x"]))

    def test_path_of_only_understands_this_buckets_urls(self):
        storage = adapter(lambda request: httpx2.Response(200))
        assert storage.path_of(PUBLIC + "recipes/u/a.webp") == "recipes/u/a.webp"
        assert storage.path_of("https://elsewhere.example/recipes/u/a.webp") is None
        assert storage.path_of("https://abcd.supabase.co/storage/v1/object/public/other-bucket/a.webp") is None


class TestEveryImageColumnIsCovered:

    def test_no_column_that_stores_an_image_url_is_missing(self):
        """A new `*_photo_url` / `avatar_url` column that the sweep does not read would have its files deleted."""
        import app.main  # noqa: F401  registers every model
        from app.shared.database.base import Base

        looks_like_an_image_url = re.compile(r"(photo|avatar|image|cover|picture).*url|url.*(photo|avatar|image)")
        found = {
            (table.name, column.name)
            for table in Base.metadata.tables.values()
            for column in table.columns
            if looks_like_an_image_url.search(column.name)
        }

        assert found == set(COLUMNS)
