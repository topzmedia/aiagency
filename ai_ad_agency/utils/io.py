"""
File I/O utilities — JSON, CSV, downloads, paths.
"""
from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar

from pydantic import BaseModel

logger = logging.getLogger("ai_ad_agency.io")

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def write_json(data: Any, path: str | Path, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=_json_default, ensure_ascii=False)
    logger.debug("Wrote JSON → %s", path)


def read_json(path: str | Path) -> Any:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_models_json(models: List[BaseModel], path: str | Path) -> None:
    write_json([m.model_dump(mode="json") for m in models], path)


def read_models_json(path: str | Path, model_cls: Type[T]) -> List[T]:
    data = read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON list at {path}, got {type(data)}")
    return [model_cls(**item) for item in data]


def append_json_line(obj: Any, path: str | Path) -> None:
    """Append a single JSON object as a newline-delimited JSON record (NDJSON)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, default=_json_default) + "\n")


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def write_csv(
    rows: List[Dict[str, Any]],
    path: str | Path,
    fieldnames: Optional[List[str]] = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # Write empty file with header only if fieldnames provided
        if fieldnames:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.debug("Wrote CSV → %s (%d rows)", path, len(rows))


def models_to_csv(models: List[BaseModel], path: str | Path) -> None:
    rows = [m.model_dump(mode="json") for m in models]
    # Flatten nested dicts for CSV
    flat_rows = [_flatten_dict(r) for r in rows]
    write_csv(flat_rows, path)


def _flatten_dict(d: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for sub_k, sub_v in _flatten_dict(v, sep).items():
                result[f"{k}{sep}{sub_k}"] = sub_v
        elif isinstance(v, list):
            result[k] = json.dumps(v, default=_json_default)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Download utilities
# ---------------------------------------------------------------------------

def download_file(url: str, dest: str | Path, timeout: int = 60) -> Path:
    """
    Download a file from URL to dest path.
    Returns the destination path.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Downloading %s → %s", url[:80], dest)

    req = urllib.request.Request(url, headers={"User-Agent": "AIAdAgency/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        with open(dest, "wb") as f:
            shutil.copyfileobj(response, f)

    size = dest.stat().st_size
    logger.debug("Downloaded %s (%.1f KB)", dest.name, size / 1024)
    return dest


def safe_download(url: str, dest: str | Path, timeout: int = 60) -> Optional[Path]:
    """Download file, returning None on failure instead of raising."""
    try:
        return download_file(url, dest, timeout=timeout)
    except Exception as e:
        logger.error("Download failed for %s: %s", url[:80], e)
        return None


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(name: str, max_len: int = 100) -> str:
    """Convert a string to a safe filename."""
    import re
    # Replace non-alphanumeric with underscore
    safe = re.sub(r"[^\w\-.]", "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe[:max_len]


def timestamped_path(base_dir: str | Path, prefix: str, suffix: str) -> Path:
    """Generate a timestamped file path."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{ts}{suffix}"
    return Path(base_dir) / filename


def get_file_size(path: str | Path) -> int:
    """Return file size in bytes, 0 if file doesn't exist."""
    try:
        return Path(path).stat().st_size
    except (FileNotFoundError, OSError):
        return 0


def copy_file(src: str | Path, dest: str | Path) -> Path:
    """Copy file, creating parent directories as needed."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dest))
    return dest


def list_files(directory: str | Path, pattern: str = "*") -> List[Path]:
    """List files matching a glob pattern in a directory."""
    return sorted(Path(directory).glob(pattern))
