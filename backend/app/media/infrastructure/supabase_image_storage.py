"""
Supabase Storage adapter for `ImageStorage`.

Uses the project's secret key (server-side only) to ask Storage for a signed
upload URL; the browser then uploads with that URL alone and never sees a key.
The bucket is public, so the stored photo is read from its public URL.
"""
from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx2

from app.media.domain.services.image_storage import ImageStorage, SignedUpload
from app.media.domain.services.image_uploader import ImageUploader
from app.media.domain.services.stored_images import StoredImage, StoredImages
from app.media.domain.upload_policy import ImageStorageUnavailableError

logger = logging.getLogger(__name__)

LIST_PAGE = 100


class SupabaseImageStorage(ImageStorage, ImageUploader, StoredImages):
    def __init__(self, project_url: str, secret_key: str, bucket: str, client: httpx2.AsyncClient | None = None) -> None:
        # Only scheme + host matter: the dashboard also shows the project URL as .../rest/v1/.
        project = urlsplit(project_url)
        self._storage_url = f"{project.scheme}://{project.netloc}/storage/v1"
        self._public_prefix = f"{self._storage_url}/object/public/{quote(bucket)}/"
        self._bucket = bucket
        self._headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}
        self._client = client

    async def create_signed_upload(self, path: str) -> SignedUpload:
        object_ref = f"{quote(self._bucket)}/{quote(path)}"
        try:
            response = await self._send("POST", f"{self._storage_url}/object/upload/sign/{object_ref}")
        except httpx2.HTTPError:
            logger.exception("Supabase Storage unreachable")
            raise ImageStorageUnavailableError()
        if response.status_code >= 400:
            # Never echo Storage's answer to the client: it may describe the project setup.
            logger.error("Supabase Storage refused a signed upload (%s): %s", response.status_code, response.text[:300])
            raise ImageStorageUnavailableError()
        # Storage answers with a path relative to /storage/v1, e.g. /object/upload/sign/<bucket>/<path>?token=...
        return SignedUpload(
            upload_url=f"{self._storage_url}{response.json()['url']}",
            public_url=f"{self._storage_url}/object/public/{object_ref}",
        )

    async def upload(self, path: str, data: bytes, content_type: str) -> str:
        """Server-side upload with the secret key (the browser path uses a signed URL instead)."""
        object_ref = f"{quote(self._bucket)}/{quote(path)}"
        headers = {**self._headers, "Content-Type": content_type, "x-upsert": "false"}
        try:
            if self._client is not None:
                response = await self._client.post(f"{self._storage_url}/object/{object_ref}", headers=headers, content=data)
            else:
                async with httpx2.AsyncClient(timeout=30) as client:
                    response = await client.post(f"{self._storage_url}/object/{object_ref}", headers=headers, content=data)
        except httpx2.HTTPError:
            logger.exception("Supabase Storage unreachable")
            raise ImageStorageUnavailableError()
        if response.status_code >= 400:
            logger.error("Supabase Storage refused an upload (%s): %s", response.status_code, response.text[:300])
            raise ImageStorageUnavailableError()
        return f"{self._storage_url}/object/public/{object_ref}"

    # --- StoredImages: used by the clean-up sweep, never by a request ---------------------

    async def list_all(self) -> list[StoredImage]:
        images: list[StoredImage] = []
        folders = [""]
        while folders:
            folder = folders.pop()
            offset = 0
            while True:
                page = await self._list(folder, offset)
                for entry in page:
                    path = f"{folder}{entry['name']}"
                    if entry.get("id") is None:  # a folder: Storage lists it without an id
                        folders.append(f"{path}/")
                    else:
                        images.append(StoredImage(path=path, created_at=_parse_time(entry.get("created_at"))))
                if len(page) < LIST_PAGE:
                    break
                offset += LIST_PAGE
        return images

    async def delete(self, paths: list[str]) -> None:
        if not paths:
            return
        response = await self._send("DELETE", f"{self._storage_url}/object/{quote(self._bucket)}", {"prefixes": paths})
        if response.status_code >= 400:
            logger.error("Supabase Storage refused a delete (%s): %s", response.status_code, response.text[:300])
            raise ImageStorageUnavailableError()

    def path_of(self, url: str) -> str | None:
        return url[len(self._public_prefix):] if url.startswith(self._public_prefix) else None

    async def _list(self, folder: str, offset: int) -> list[dict]:
        body = {"prefix": folder, "limit": LIST_PAGE, "offset": offset, "sortBy": {"column": "name", "order": "asc"}}
        response = await self._send("POST", f"{self._storage_url}/object/list/{quote(self._bucket)}", body)
        if response.status_code >= 400:
            logger.error("Supabase Storage refused a listing (%s): %s", response.status_code, response.text[:300])
            raise ImageStorageUnavailableError()
        return response.json()

    async def _send(self, method: str, url: str, json: dict | None = None) -> httpx2.Response:
        if self._client is not None:
            return await self._client.request(method, url, headers=self._headers, json=json)
        async with httpx2.AsyncClient(timeout=20) as client:
            return await client.request(method, url, headers=self._headers, json=json)


def _parse_time(raw: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(raw) if raw else None
    except ValueError:
        return None
