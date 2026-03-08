"""
Validation helpers for configs, files, and media assets.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("ai_ad_agency.validators")


def validate_file_exists(path: str | Path) -> Tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"File not found: {p}"
    if not p.is_file():
        return False, f"Path is not a file: {p}"
    return True, ""


def validate_file_size(path: str | Path, min_bytes: int = 1) -> Tuple[bool, str]:
    ok, msg = validate_file_exists(path)
    if not ok:
        return False, msg
    size = Path(path).stat().st_size
    if size < min_bytes:
        return False, f"File too small ({size} bytes < {min_bytes} bytes): {path}"
    return True, ""


def validate_video_file(
    path: str | Path,
    min_size_bytes: int = 50_000,
    min_duration: float = 1.0,
) -> Tuple[bool, List[str]]:
    """
    Validate a video file using ffprobe.
    Returns (passed, list_of_issues).
    """
    issues: List[str] = []

    ok, msg = validate_file_size(path, min_bytes=min_size_bytes)
    if not ok:
        issues.append(msg)
        return False, issues

    # Try ffprobe for media info
    info = probe_media(str(path))
    if info is None:
        issues.append(f"ffprobe failed or unavailable for: {path}")
        return False, issues

    duration = info.get("duration", 0.0)
    if duration < min_duration:
        issues.append(f"Duration too short ({duration:.2f}s < {min_duration}s)")

    has_video = info.get("has_video", False)
    has_audio = info.get("has_audio", False)

    if not has_video:
        issues.append("No video stream found")
    if not has_audio:
        issues.append("No audio stream found")

    return len(issues) == 0, issues


def validate_image_file(
    path: str | Path,
    min_size_bytes: int = 5_000,
) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    ok, msg = validate_file_size(path, min_bytes=min_size_bytes)
    if not ok:
        issues.append(msg)
        return False, issues

    try:
        from PIL import Image
        with Image.open(path) as img:
            img.verify()
    except Exception as e:
        issues.append(f"Image validation failed: {e}")
        return False, issues

    return True, []


def probe_media(path: str) -> Optional[dict]:
    """
    Run ffprobe to get media stream info.
    Returns dict with keys: duration, width, height, has_video, has_audio.
    Returns None if ffprobe is unavailable.
    """
    import json
    import subprocess

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.debug("ffprobe error for %s: %s", path, result.stderr[:200])
            return None

        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        info: dict = {
            "duration": float(fmt.get("duration", 0.0)),
            "has_video": False,
            "has_audio": False,
            "width": 0,
            "height": 0,
        }
        for stream in streams:
            codec_type = stream.get("codec_type", "")
            if codec_type == "video":
                info["has_video"] = True
                info["width"] = stream.get("width", 0)
                info["height"] = stream.get("height", 0)
                if info["duration"] == 0:
                    info["duration"] = float(stream.get("duration", 0))
            elif codec_type == "audio":
                info["has_audio"] = True

        return info

    except FileNotFoundError:
        logger.debug("ffprobe not found in PATH")
        return None
    except Exception as e:
        logger.debug("ffprobe exception: %s", e)
        return None


def validate_api_key(key: str, label: str = "API key") -> Tuple[bool, str]:
    if not key or not key.strip():
        return False, f"{label} is not set"
    if len(key) < 10:
        return False, f"{label} looks too short (len={len(key)})"
    return True, ""


def validate_url(url: str) -> Tuple[bool, str]:
    if not url:
        return False, "URL is empty"
    if not url.startswith(("http://", "https://")):
        return False, f"URL must start with http:// or https://, got: {url[:30]}"
    return True, ""
