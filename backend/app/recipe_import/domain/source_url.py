"""
The video link a recipe is imported from.

Only TikTok videos and Instagram Reels (posts and IGTV, which Instagram serves from the
same player) are accepted. The link is checked strictly — https, a known host, a video path —
because it is handed to an external provider on the user's behalf: nothing else may
travel through this door.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit, urlunsplit

from app.shared.exceptions.domain_exceptions import ValidationError

MAX_URL_LENGTH = 500


class VideoPlatform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class UnsupportedVideoUrlError(ValidationError):
    def __init__(self) -> None:
        super().__init__("Only links to a TikTok video or an Instagram Reel can be imported")


@dataclass(frozen=True)
class SourceUrl:
    platform: VideoPlatform
    url: str  # canonical: https, no fragment, no tracking query


# Short links (vm./vt.tiktok.com) redirect to the video: the provider follows them.
_TIKTOK_HOSTS = {"tiktok.com", "www.tiktok.com", "m.tiktok.com", "vm.tiktok.com", "vt.tiktok.com"}
_INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
_TIKTOK_SHORT_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}
_TIKTOK_VIDEO = re.compile(r"^(/@[\w.\-]+/video/\d+|/v/\d+(\.html)?|/t/[\w\-]+/?)$")
_TIKTOK_SHORT = re.compile(r"^/[\w\-]{6,20}/?$")
_INSTAGRAM_VIDEO = re.compile(r"^(/[\w.]+)?/(reel|reels|p|tv)/[\w\-]+/?$")


def parse_source_url(raw: str) -> SourceUrl:
    text = (raw or "").strip()
    if not text or len(text) > MAX_URL_LENGTH:
        raise UnsupportedVideoUrlError()
    try:
        parts = urlsplit(text if "://" in text else f"https://{text}")
        host = (parts.hostname or "").lower()
        port = parts.port  # raises ValueError for "javascript:alert(1)" and friends
    except ValueError:
        raise UnsupportedVideoUrlError()
    if parts.scheme not in ("http", "https") or parts.username or parts.password or port not in (None, 443, 80):
        raise UnsupportedVideoUrlError()

    if host in _TIKTOK_HOSTS and _TIKTOK_VIDEO.match(parts.path) or host in _TIKTOK_SHORT_HOSTS and _TIKTOK_SHORT.match(parts.path):
        platform = VideoPlatform.TIKTOK
    elif host in _INSTAGRAM_HOSTS and _INSTAGRAM_VIDEO.match(parts.path):
        platform = VideoPlatform.INSTAGRAM
    else:
        raise UnsupportedVideoUrlError()

    # Tracking parameters (?igsh=..., ?utm_...) add nothing and identify the person who shared it.
    return SourceUrl(platform, urlunsplit(("https", parts.netloc.lower().replace(":80", "").replace(":443", ""), parts.path, "", "")))
