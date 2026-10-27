"""
The one place that picks the image storage provider from settings.

The API and the clean-up command both come here, so switching providers means
changing this function only.
"""
from __future__ import annotations

from app.media.infrastructure.supabase_image_storage import SupabaseImageStorage
from app.shared.config.settings import get_settings


def configured_image_storage() -> SupabaseImageStorage | None:
    """The storage adapter, or None when this environment has no storage configured."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    return SupabaseImageStorage(settings.supabase_url, settings.supabase_service_key, settings.supabase_storage_bucket)
