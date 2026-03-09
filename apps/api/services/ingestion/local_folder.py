"""Local folder ingestion adapter.

Scans a directory for video files (mp4, mov, webm) and creates candidate
video records using metadata extracted from the filename and ffprobe.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from apps.api.services.ingestion.base import (
    AbstractIngestionAdapter,
    CandidateVideoCreate,
    RawRecord,
)

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}


class LocalFolderAdapter(AbstractIngestionAdapter):
    """Ingest video files from a local directory."""

    @property
    def source_name(self) -> str:
        return "local_folder"

    def validate_config(self, config: dict[str, Any]) -> bool:
        folder = config.get("folder")
        if not folder:
            raise ValueError("Config must include 'folder' path")
        p = Path(folder)
        if not p.exists():
            raise ValueError(f"Folder does not exist: {folder}")
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {folder}")
        return True

    def enumerate_records(self, config: dict[str, Any]) -> Iterator[RawRecord]:
        folder = Path(config["folder"])
        recursive = config.get("recursive", True)

        pattern = "**/*" if recursive else "*"
        for file_path in sorted(folder.glob(pattern)):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                data: dict[str, Any] = {
                    "file_path": str(file_path),
                    "filename": file_path.name,
                    "stem": file_path.stem,
                    "extension": file_path.suffix.lower(),
                    "file_size": file_path.stat().st_size,
                }

                # Attempt ffprobe for metadata
                try:
                    from apps.api.services.media_prep import probe_media
                    info = probe_media(file_path)
                    data["duration_sec"] = info.duration_sec
                    data["width"] = info.width
                    data["height"] = info.height
                    data["fps"] = info.fps
                    data["video_codec"] = info.video_codec
                    data["audio_codec"] = info.audio_codec
                except Exception as exc:
                    logger.debug("ffprobe failed for %s: %s", file_path, exc)

                yield RawRecord(source_ref=str(file_path), data=data)

    def normalize_record(self, raw: RawRecord) -> CandidateVideoCreate:
        data = raw.data
        file_path = data["file_path"]
        stem = data.get("stem", "")

        # Try to extract metadata from filename patterns
        # e.g. "2024-01-15_tiktok_crashvideo" or "car_crash_highway"
        caption = _filename_to_caption(stem)
        hashtags = _extract_hashtags_from_filename(stem)
        platform = _guess_platform(stem)

        return CandidateVideoCreate(
            external_id=None,
            platform=platform,
            source_url=f"file://{file_path}",
            creator_handle=None,
            creator_name=None,
            caption_text=caption,
            hashtags_json=hashtags if hashtags else None,
            publish_date=None,
            duration_sec=data.get("duration_sec"),
            language=None,
            region_hint=None,
            local_media_path=file_path,
            metadata_json={
                "width": data.get("width"),
                "height": data.get("height"),
                "fps": data.get("fps"),
                "video_codec": data.get("video_codec"),
                "audio_codec": data.get("audio_codec"),
                "file_size": data.get("file_size"),
            },
            ingestion_source="local_folder",
        )


# ---------------------------------------------------------------------------
# Filename parsing helpers
# ---------------------------------------------------------------------------

def _filename_to_caption(stem: str) -> str:
    """Convert a filename stem to a readable caption."""
    # Replace underscores, hyphens, camelCase with spaces
    caption = re.sub(r"[_\-]", " ", stem)
    caption = re.sub(r"([a-z])([A-Z])", r"\1 \2", caption)
    # Remove date-like prefixes
    caption = re.sub(r"^\d{4}[\s\-]\d{2}[\s\-]\d{2}\s*", "", caption)
    return caption.strip().title() if caption.strip() else stem


def _extract_hashtags_from_filename(stem: str) -> list[str]:
    """Extract hashtag-like tokens from a filename."""
    tokens = re.findall(r"[a-zA-Z]+", stem)
    return [f"#{t.lower()}" for t in tokens if len(t) > 2]


def _guess_platform(stem: str) -> str:
    """Guess the source platform from filename keywords."""
    stem_lower = stem.lower()
    platforms = {
        "tiktok": "tiktok",
        "instagram": "instagram",
        "youtube": "youtube",
        "twitter": "twitter",
        "facebook": "facebook",
        "snapchat": "snapchat",
    }
    for keyword, platform in platforms.items():
        if keyword in stem_lower:
            return platform
    return "local"
