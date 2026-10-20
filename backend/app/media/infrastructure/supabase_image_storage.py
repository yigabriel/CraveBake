"""
Supabase Storage adapter for `ImageStorage`.

Uses the project's secret key (server-side only) to ask Storage for a signed
upload URL; the browser then uploads with that URL alone and never sees a key.
The bucket is public, so the stored photo is read from its public URL.
"""
from __future__ import annotations

import logging
from urllib.parse import quote, urlsplit

import httpx2

from app.media.domain.services.image_storage import ImageStorage, SignedUpload
from app.media.domain.upload_policy import ImageStorageUnavailableError

logger = logging.getLogger(__name__)


class SupabaseImageStorage(ImageStorage):
    def __init__(self, project_url: str, secret_key: str, bucket: str, client: httpx2.AsyncClient | None = None) -> None:
        # Only scheme + host matter: the dashboard also shows the project URL as .../rest/v1/.
        project = urlsplit(project_url)
        self._storage_url = f"{project.scheme}://{project.netloc}/storage/v1"
        self._bucket = bucket
        self._headers = {"apikey": secret_key, "Authorization": f"Bearer {secret_key}"}
        self._client = client

    async def create_signed_upload(self, path: str) -> SignedUpload:
        object_ref = f"{quote(self._bucket)}/{quote(path)}"
        try:
            response = await self._post(f"{self._storage_url}/object/upload/sign/{object_ref}")
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

    async def _post(self, url: str) -> httpx2.Response:
        if self._client is not None:
            return await self._client.post(url, headers=self._headers)
        async with httpx2.AsyncClient(timeout=10) as client:
            return await client.post(url, headers=self._headers)
