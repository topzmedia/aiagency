"""Direct URL stub ingestion adapter.

Takes a list of URLs (with optional metadata) and creates candidate_video
records as stubs – i.e. no local media file is downloaded at this stage.
A separate download/media-fetch step can resolve them later.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Iterator
from urllib.parse import urlparse

from apps.api.services.ingestion.base import (
    AbstractIngestionAdapter,
    CandidateVideoCreate,
    RawRecord,
)

logger = logging.getLogger(__name__)

# Platform detection from URL hostname
_PLATFORM_MAP: dict[str, str] = {
    "tiktok.com": "tiktok",
    "vm.tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "facebook.com": "facebook",
    "fb.watch": "facebook",
    "snapchat.com": "snapchat",
    "vimeo.com": "vimeo",
    "reddit.com": "reddit",
}


class URLStubAdapter(AbstractIngestionAdapter):
    """Ingest candidate videos from a list of URLs."""

    @property
    def source_name(self) -> str:
        return "url_stub"

    def validate_config(self, config: dict[str, Any]) -> bool:
        urls = config.get("urls")
        if not urls:
            raise ValueError("Config must include 'urls' (list of URL strings or dicts)")
        if not isinstance(urls, list):
            raise ValueError("'urls' must be a list")
        if len(urls) == 0:
            raise ValueError("'urls' list is empty")
        return True

    def enumerate_records(self, config: dict[str, Any]) -> Iterator[RawRecord]:
        urls = config["urls"]

        for idx, entry in enumerate(urls):
            if isinstance(entry, str):
                data = {"url": entry.strip()}
            elif isinstance(entry, dict):
                data = dict(entry)
                if "url" not in data:
                    logger.warning("URL entry %d missing 'url' key, skipping", idx)
                    continue
            else:
                logger.warning("URL entry %d has unexpected type %s, skipping", idx, type(entry))
                continue

            yield RawRecord(
                source_ref=f"url_{idx}:{data['url']}",
                data=data,
            )

    def normalize_record(self, raw: RawRecord) -> CandidateVideoCreate:
        data = raw.data
        url = data["url"].strip()

        if not url:
            raise ValueError("Empty URL")

        # Validate URL format
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        platform = _detect_platform(parsed.netloc)
        creator_handle = data.get("creator_handle")
        creator_name = data.get("creator_name")
        caption_text = data.get("caption_text")
        hashtags = data.get("hashtags")

        # Parse hashtags if string
        if isinstance(hashtags, str):
            hashtags = [t.strip() for t in hashtags.replace(",", " ").split() if t.strip()]

        publish_date = None
        pd_raw = data.get("publish_date")
        if pd_raw:
            try:
                publish_date = datetime.fromisoformat(str(pd_raw))
            except (ValueError, TypeError):
                pass

        duration_sec = None
        dur_raw = data.get("duration_sec")
        if dur_raw is not None:
            try:
                duration_sec = float(dur_raw)
            except (ValueError, TypeError):
                pass

        return CandidateVideoCreate(
            external_id=_extract_external_id(url, platform),
            platform=platform,
            source_url=url,
            canonical_url=url,
            creator_handle=creator_handle,
            creator_name=creator_name,
            caption_text=caption_text,
            hashtags_json=hashtags,
            publish_date=publish_date,
            duration_sec=duration_sec,
            language=data.get("language"),
            region_hint=data.get("region_hint"),
            local_media_path=None,  # stub – no local file
            metadata_json={k: v for k, v in data.items()
                           if k not in ("url", "creator_handle", "creator_name",
                                        "caption_text", "hashtags", "publish_date",
                                        "duration_sec", "language", "region_hint")},
            ingestion_source="url_stub",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_platform(hostname: str) -> str:
    """Detect platform from URL hostname."""
    hostname = hostname.lower().lstrip("www.")
    for domain, platform in _PLATFORM_MAP.items():
        if hostname == domain or hostname.endswith("." + domain):
            return platform
    return "unknown"


def _extract_external_id(url: str, platform: str) -> str | None:
    """Try to extract a platform-specific ID from the URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    if platform == "youtube":
        # youtube.com/watch?v=ABC or youtu.be/ABC
        if "youtu.be" in parsed.netloc:
            return path.split("/")[0] if path else None
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]

    if platform == "tiktok":
        # tiktok.com/@user/video/123456
        match = re.search(r"/video/(\d+)", path)
        return match.group(1) if match else None

    # Generic: use last path segment
    segments = [s for s in path.split("/") if s]
    return segments[-1] if segments else None
