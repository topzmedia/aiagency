"""Query interpreter service.

Parses raw query strings into structured search descriptors using rule-based
NLP techniques.  No external LLM is required; parsing relies on configurable
synonym dictionaries, POS-like heuristics, and pattern matching.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synonym dictionaries – seed terms mapped to expansion lists
# ---------------------------------------------------------------------------

SYNONYM_DICT: dict[str, list[str]] = {
    "car crash": ["collision", "wreck", "accident", "dashcam", "impact", "fender bender"],
    "roof damage": ["storm damage", "hail", "missing shingles", "wind damage"],
    "kitchen": ["island", "cabinets", "marble", "pendant lights", "countertop"],
    "arguing": ["yelling", "confrontation", "dispute", "fight", "screaming"],
    "smiling couple": ["happy family", "kitchen table", "home interior"],
    "dog": ["puppy", "canine", "pet"],
    "snow": ["winter", "blizzard", "frost", "ice"],
    "luxury": ["high-end", "premium", "upscale", "elegant"],
}

# Build reverse map: expansion term -> canonical form
_REVERSE_SYNONYMS: dict[str, str] = {}
for _canonical, _expansions in SYNONYM_DICT.items():
    for _exp in _expansions:
        _REVERSE_SYNONYMS[_exp.lower()] = _canonical

# ---------------------------------------------------------------------------
# Lightweight word classification lists
# ---------------------------------------------------------------------------

_ENTITY_NOUNS = {
    "car", "truck", "vehicle", "person", "people", "dog", "puppy", "canine",
    "pet", "roof", "house", "home", "kitchen", "table", "phone", "fire",
    "road", "tree", "building", "water", "sky", "couple", "family", "child",
    "baby", "camera", "dashcam", "shingles", "hail", "snow", "ice",
    "island", "cabinets", "marble", "countertop", "lights", "restaurant",
    "store", "office", "construction", "damage", "wreck",
}

_ACTION_VERBS = {
    "crash", "hit", "drive", "walk", "run", "play", "argue", "yell",
    "scream", "smile", "laugh", "cook", "eat", "inspect", "repair",
    "dance", "fight", "celebrate", "bark", "sing", "cry", "cheer",
    "fall", "slide", "climb", "jump", "throw", "catch",
}

_SCENE_INDICATORS: dict[str, list[str]] = {
    "road_highway": ["road", "highway", "driving", "dashcam", "car", "truck", "vehicle"],
    "indoor_kitchen": ["kitchen", "island", "cabinets", "countertop", "cooking"],
    "suburban_exterior": ["house", "roof", "shingles", "yard", "driveway", "suburban"],
    "snow_outdoors": ["snow", "winter", "blizzard", "frost", "ice"],
    "residential_interior": ["home", "interior", "living room", "bedroom", "family"],
    "outdoor_urban": ["city", "street", "building", "urban"],
    "outdoor_rural": ["farm", "field", "rural", "country"],
    "construction_site": ["construction", "scaffold", "crane", "site"],
    "office": ["office", "desk", "computer", "cubicle"],
    "store": ["store", "shop", "mall", "retail"],
    "restaurant": ["restaurant", "dining", "waiter", "menu"],
}

_AUDIO_CUE_MAP: dict[str, list[str]] = {
    "impact": ["crash", "collision", "hit", "wreck", "smash"],
    "screech": ["screech", "brake", "skid"],
    "bark": ["dog", "bark", "puppy"],
    "thunder": ["thunder", "storm", "lightning"],
    "cheering": ["cheer", "celebrate", "crowd"],
    "crying": ["cry", "sob", "weep"],
    "speech": ["argue", "yell", "scream", "talk", "speak"],
}


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuery:
    raw_query: str
    entities: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    scenes: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    audio_events: list[str] = field(default_factory=list)
    ocr_terms: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    positive_examples: list[str] = field(default_factory=list)
    negative_examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_query": self.raw_query,
            "entities": self.entities,
            "actions": self.actions,
            "scenes": self.scenes,
            "attributes": self.attributes,
            "audio_events": self.audio_events,
            "ocr_terms": self.ocr_terms,
            "synonyms": self.synonyms,
            "exclude": self.exclude,
            "positive_examples": self.positive_examples,
            "negative_examples": self.negative_examples,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lowercase and split into tokens, stripping punctuation."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def _bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i + 1]}" for i in range(len(tokens) - 1)]


def _trigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i + 1]} {tokens[i + 2]}" for i in range(len(tokens) - 2)]


def _extract_entities(tokens: list[str]) -> list[str]:
    return sorted({t for t in tokens if t in _ENTITY_NOUNS})


def _extract_actions(tokens: list[str]) -> list[str]:
    return sorted({t for t in tokens if t in _ACTION_VERBS})


def _infer_scenes(tokens: list[str], ngrams: list[str]) -> list[str]:
    all_terms = set(tokens) | set(ngrams)
    scenes: list[str] = []
    for scene_label, indicators in _SCENE_INDICATORS.items():
        if all_terms & set(indicators):
            scenes.append(scene_label)
    return sorted(set(scenes))


def _derive_audio_events(tokens: list[str]) -> list[str]:
    events: list[str] = []
    for label, triggers in _AUDIO_CUE_MAP.items():
        if set(tokens) & set(triggers):
            events.append(label)
    return sorted(set(events))


def _expand_synonyms(tokens: list[str], ngrams: list[str]) -> list[str]:
    """Return all synonym expansions for tokens and n-grams found in the
    synonym dictionary."""
    syns: set[str] = set()
    all_terms = set(tokens) | set(ngrams)

    # Check canonical keys
    for canonical, expansions in SYNONYM_DICT.items():
        canonical_lower = canonical.lower()
        if canonical_lower in all_terms or canonical_lower in " ".join(tokens):
            syns.update(expansions)

    # Check reverse map
    for term in all_terms:
        if term in _REVERSE_SYNONYMS:
            canonical = _REVERSE_SYNONYMS[term]
            syns.update(SYNONYM_DICT.get(canonical, []))
            syns.add(canonical)

    return sorted(syns)


def _derive_ocr_terms(entities: list[str], actions: list[str], synonyms: list[str]) -> list[str]:
    """OCR search terms are the union of entities, action keywords, and select
    synonyms that might appear as on-screen text."""
    candidates: set[str] = set()
    candidates.update(entities)
    candidates.update(actions)
    # Add short synonym phrases likely to appear as captions/overlays
    for s in synonyms:
        if len(s.split()) <= 3:
            candidates.add(s)
    return sorted(candidates)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def interpret_query(
    raw_query: str,
    include_filters: dict[str, Any] | None = None,
    exclude_filters: dict[str, Any] | None = None,
) -> ParsedQuery:
    """Parse a raw query string into a structured :class:`ParsedQuery`.

    Parameters
    ----------
    raw_query:
        Free-text search query from the user.
    include_filters:
        Optional dict of include constraints (e.g. ``{"platform": "tiktok"}``).
    exclude_filters:
        Optional dict of exclusion constraints (e.g. ``{"terms": ["music video"]}``).
    """
    include_filters = include_filters or {}
    exclude_filters = exclude_filters or {}

    tokens = _tokenize(raw_query)
    ngrams = _bigrams(tokens) + _trigrams(tokens)

    entities = _extract_entities(tokens)
    actions = _extract_actions(tokens)
    scenes = _infer_scenes(tokens, ngrams)
    synonyms = _expand_synonyms(tokens, ngrams)
    audio_events = _derive_audio_events(tokens)
    ocr_terms = _derive_ocr_terms(entities, actions, synonyms)

    # Attributes: adjectives / qualifiers that are not entities or actions
    known = set(entities) | set(actions)
    attributes = sorted({t for t in tokens if t not in known and len(t) > 2})

    # Process exclude filters
    exclude_terms: list[str] = []
    if "terms" in exclude_filters:
        exclude_terms.extend(exclude_filters["terms"])

    # Positive / negative examples from filters
    positive_examples: list[str] = include_filters.get("examples", [])
    negative_examples: list[str] = exclude_filters.get("examples", [])

    parsed = ParsedQuery(
        raw_query=raw_query,
        entities=entities,
        actions=actions,
        scenes=scenes,
        attributes=attributes,
        audio_events=audio_events,
        ocr_terms=ocr_terms,
        synonyms=synonyms,
        exclude=exclude_terms,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
    )

    logger.info("Interpreted query: %s -> %d entities, %d actions, %d scenes",
                raw_query, len(entities), len(actions), len(scenes))
    return parsed
