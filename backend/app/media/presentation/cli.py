"""
Command line for the storage clean-up:

    python -m app.media.presentation.cli                 # dry run: only lists what would go
    python -m app.media.presentation.cli --apply         # deletes the orphaned files
    python -m app.media.presentation.cli --min-age-hours 72

Reads the database and the storage from the same settings as the API, so run it
wherever the API's environment variables are (your machine with backend/.env, or
Render's shell). A dry run is the default on purpose.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta

from app.media.application.use_cases.clean_orphaned_images_use_case import CleanOrphanedImagesUseCase
from app.media.domain.upload_policy import ImageStorageUnavailableError
from app.media.infrastructure.sql_image_references import SqlImageReferences
from app.media.infrastructure.supabase_image_storage import SupabaseImageStorage
from app.shared.config.settings import get_settings


async def run(apply: bool, min_age_hours: float, force: bool) -> int:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        print("SUPABASE_URL and SUPABASE_SERVICE_KEY are not set: nothing to clean.")
        return 1
    # Imported here: it opens the database engine, which --help does not need.
    from app.shared.database.session import AsyncSessionFactory, engine

    engine.echo = False  # the API logs every SQL statement in debug; a report should not

    storage = SupabaseImageStorage(settings.supabase_url, settings.supabase_service_key, settings.supabase_storage_bucket)
    try:
        async with AsyncSessionFactory() as session:
            report = await CleanOrphanedImagesUseCase(storage, SqlImageReferences(session)).execute(
                timedelta(hours=min_age_hours), apply=apply, force=force
            )
    except ImageStorageUnavailableError as error:
        print(f"Storage unavailable: {error}")
        return 1

    print(f"Files in storage: {report.stored}")
    print(f"Still referenced: {report.referenced}")
    print(f"Too recent to touch (< {min_age_hours:g} h): {report.too_recent}")
    print(f"Orphaned: {len(report.orphans)}")
    for path in report.orphans:
        print(f"  {path}")
    if apply:
        print(f"Deleted: {report.deleted}")
    elif report.orphans:
        print("Dry run: nothing was deleted. Run again with --apply to delete them.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete files in image storage that no photo or avatar references.")
    parser.add_argument("--apply", action="store_true", help="actually delete (default: only report)")
    parser.add_argument("--min-age-hours", type=float, default=24, help="never touch files newer than this (default 24)")
    parser.add_argument("--force", action="store_true", help="delete even if the database references no file at all")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.apply, args.min_age_hours, args.force)))


if __name__ == "__main__":
    main()
