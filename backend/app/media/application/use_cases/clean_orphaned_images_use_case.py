"""
CleanOrphanedImagesUseCase — deletes files in storage that nothing references any more.

Why a sweep and not "delete the file when the photo is removed": the URL may still
be in use elsewhere (a personalized copy of the recipe, a preparation in progress),
so only the full picture of what is referenced can say a file is garbage.

Safety rails:
- A file younger than `min_age` is never touched: it may have just been uploaded and
  not attached yet (the upload and "save" are two requests).
- If storage has files but nothing references any of them, the references probably
  were not read right (wrong database?): the sweep refuses instead of deleting everything.
- Without `apply` it only reports (dry run).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.media.domain.services.image_references import ImageReferences
from app.media.domain.services.stored_images import StoredImages
from app.shared.exceptions.domain_exceptions import ValidationError

BATCH = 100


class CleanupRefusedError(ValidationError):
    def __init__(self) -> None:
        super().__init__(
            "Storage has files but no URL in the database points to any of them. "
            "Refusing to delete: check that this is the right database, or pass force."
        )


@dataclass
class CleanupReport:
    stored: int = 0
    referenced: int = 0
    too_recent: int = 0
    orphans: list[str] = field(default_factory=list)
    deleted: int = 0


class CleanOrphanedImagesUseCase:
    def __init__(
        self,
        storage: StoredImages,
        references: ImageReferences,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._storage = storage
        self._references = references
        self._now = now

    async def execute(self, min_age: timedelta, apply: bool = False, force: bool = False) -> CleanupReport:
        stored = await self._storage.list_all()
        in_use = {path for url in await self._references.urls() if (path := self._storage.path_of(url))}

        report = CleanupReport(stored=len(stored), referenced=sum(1 for image in stored if image.path in in_use))
        if stored and not in_use and not force:
            raise CleanupRefusedError()

        cutoff = self._now() - min_age
        for image in stored:
            if image.path in in_use:
                continue
            if image.created_at is None or image.created_at > cutoff:
                report.too_recent += 1
                continue
            report.orphans.append(image.path)

        if apply:
            for start in range(0, len(report.orphans), BATCH):
                batch = report.orphans[start : start + BATCH]
                await self._storage.delete(batch)
                report.deleted += len(batch)
        return report
