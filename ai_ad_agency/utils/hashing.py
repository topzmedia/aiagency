"""
File hashing utilities for deduplication and integrity checks.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional


def hash_file(path: str | Path, algorithm: str = "sha256", chunk_size: int = 65536) -> str:
    """
    Compute cryptographic hash of a file's contents.

    Args:
        path: Path to the file.
        algorithm: Hash algorithm (sha256, md5, sha1).
        chunk_size: Read chunk size in bytes.

    Returns:
        Hex digest string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def hash_string(s: str, algorithm: str = "sha256") -> str:
    """Compute hash of a string."""
    h = hashlib.new(algorithm)
    h.update(s.encode("utf-8"))
    return h.hexdigest()


def hash_dict(d: dict, algorithm: str = "sha256") -> str:
    """Compute deterministic hash of a dictionary (sorted keys)."""
    import json
    serialized = json.dumps(d, sort_keys=True, default=str)
    return hash_string(serialized, algorithm)


def short_hash(value: str, length: int = 8) -> str:
    """Return a short hex hash useful for IDs."""
    return hash_string(value)[:length]


def safe_hash_file(path: str | Path) -> Optional[str]:
    """Hash a file, returning None if it doesn't exist or can't be read."""
    try:
        return hash_file(path)
    except (FileNotFoundError, PermissionError, OSError):
        return None
