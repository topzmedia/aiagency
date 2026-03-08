"""
Deduplication utilities.
Detects exact duplicates (hash-based) and near-duplicates (field combo + string similarity).
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

from .hashing import hash_dict, hash_string

logger = logging.getLogger("ai_ad_agency.dedupe")


# ---------------------------------------------------------------------------
# String similarity
# ---------------------------------------------------------------------------

def string_similarity(a: str, b: str) -> float:
    """Return 0-1 similarity score between two strings (SequenceMatcher)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_near_duplicate_text(
    a: str,
    b: str,
    threshold: float = 0.85,
) -> bool:
    """Return True if texts are similar above the threshold."""
    return string_similarity(a, b) >= threshold


# ---------------------------------------------------------------------------
# Hash-based dedupe for collections
# ---------------------------------------------------------------------------

class TextDedupe:
    """
    Tracks seen text hashes and similarity for deduplication of generated text.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold
        self._seen_hashes: Set[str] = set()
        self._seen_texts: List[str] = []
        self.duplicates_rejected: int = 0
        self.near_duplicates_rejected: int = 0

    def is_duplicate(self, text: str) -> bool:
        """Check exact hash duplicate."""
        h = hash_string(text)
        return h in self._seen_hashes

    def is_near_duplicate(self, text: str) -> bool:
        """Check near-duplicate via similarity scan."""
        for seen in self._seen_texts:
            if is_near_duplicate_text(text, seen, self.threshold):
                return True
        return False

    def add(self, text: str) -> bool:
        """
        Add text if it's not a duplicate.
        Returns True if added, False if rejected.
        """
        h = hash_string(text)
        if h in self._seen_hashes:
            self.duplicates_rejected += 1
            logger.debug("Exact duplicate rejected: %s...", text[:50])
            return False

        if self.is_near_duplicate(text):
            self.near_duplicates_rejected += 1
            logger.debug("Near-duplicate rejected: %s...", text[:50])
            return False

        self._seen_hashes.add(h)
        self._seen_texts.append(text)
        return True

    def filter(self, texts: List[str]) -> List[str]:
        """Filter a list, returning only unique texts."""
        results = []
        for text in texts:
            if self.add(text):
                results.append(text)
        return results

    def stats(self) -> Dict[str, int]:
        return {
            "accepted": len(self._seen_texts),
            "exact_duplicates_rejected": self.duplicates_rejected,
            "near_duplicates_rejected": self.near_duplicates_rejected,
        }


# ---------------------------------------------------------------------------
# Metadata-based dedupe for creative variants
# ---------------------------------------------------------------------------

class MetadataDedupe:
    """
    Deduplicate creative variants based on key field combinations.
    Prevents generating the same hook+avatar+script combo twice.
    """

    def __init__(self, key_fields: List[str]):
        self.key_fields = key_fields
        self._seen_combos: Set[str] = set()
        self.rejected: int = 0

    def _make_key(self, record: Dict[str, Any]) -> str:
        combo = {k: record.get(k, "") for k in self.key_fields}
        return hash_dict(combo)

    def is_duplicate(self, record: Dict[str, Any]) -> bool:
        key = self._make_key(record)
        return key in self._seen_combos

    def add(self, record: Dict[str, Any]) -> bool:
        """Return True if added (not a duplicate)."""
        key = self._make_key(record)
        if key in self._seen_combos:
            self.rejected += 1
            return False
        self._seen_combos.add(key)
        return True

    def filter(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for r in records:
            if self.add(r):
                result.append(r)
        return result


# ---------------------------------------------------------------------------
# File hash dedupe
# ---------------------------------------------------------------------------

class FileDedupe:
    """Track file content hashes to detect duplicate output files."""

    def __init__(self) -> None:
        self._seen_hashes: Set[str] = set()
        self.rejected: int = 0

    def check_and_add(self, file_hash: str) -> bool:
        """Return True if this is a new unique file."""
        if file_hash in self._seen_hashes:
            self.rejected += 1
            return False
        self._seen_hashes.add(file_hash)
        return True

    def is_duplicate(self, file_hash: str) -> bool:
        return file_hash in self._seen_hashes


# ---------------------------------------------------------------------------
# Dedupe list of strings in one call
# ---------------------------------------------------------------------------

def dedupe_texts(
    texts: List[str],
    similarity_threshold: float = 0.85,
) -> Tuple[List[str], int, int]:
    """
    Deduplicate a list of strings.
    Returns (unique_texts, exact_dupes_removed, near_dupes_removed).
    """
    deduper = TextDedupe(similarity_threshold=similarity_threshold)
    unique = deduper.filter(texts)
    stats = deduper.stats()
    return unique, stats["exact_duplicates_rejected"], stats["near_duplicates_rejected"]
