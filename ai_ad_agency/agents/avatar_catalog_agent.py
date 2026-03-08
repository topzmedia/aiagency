"""
Avatar Catalog Agent — builds and manages a catalog of 60+ realistic AI avatars.
Handles loading, saving, syncing from provider, filtering, and batch selection with diversity quotas.
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.enums import AgeGroup, AppearanceTag, AvatarProvider, GenderPresentation, WardrobeStyle
from ..models.schemas import AvatarMetadata
from ..providers.avatar_provider import BaseAvatarProvider
from ..utils.config import AppConfig
from ..utils.io import write_models_json, read_models_json
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("avatar_catalog_agent")


# ---------------------------------------------------------------------------
# Built-in catalog — 60 realistic avatar entries
# ---------------------------------------------------------------------------

_BUILTIN_CATALOG: List[Dict[str, Any]] = [
    # ── Young Adult Masculine (10) ──────────────────────────────────────────
    {
        "avatar_id": "avatar-001",
        "provider": AvatarProvider.HEYGEN,
        "name": "Marcus",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "energetic",
        "realism_score": 8.5,
        "preview_url": "https://static.heygen.ai/avatars/avatar-001.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Energetic young adult, casual style, high engagement",
    },
    {
        "avatar_id": "avatar-002",
        "provider": AvatarProvider.HEYGEN,
        "name": "Liam",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-002.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Professional look, business casual, trustworthy demeanor",
    },
    {
        "avatar_id": "avatar-003",
        "provider": AvatarProvider.HEYGEN,
        "name": "Diego",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 8.2,
        "preview_url": "https://static.heygen.ai/avatars/avatar-003.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Relatable everyday look, warm and approachable",
    },
    {
        "avatar_id": "avatar-004",
        "provider": AvatarProvider.HEYGEN,
        "name": "Chen Wei",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-004.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Professional presenter, authoritative tone",
    },
    {
        "avatar_id": "avatar-005",
        "provider": AvatarProvider.HEYGEN,
        "name": "Arjun",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.3,
        "preview_url": "https://static.heygen.ai/avatars/avatar-005.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Friendly casual presenter",
    },
    {
        "avatar_id": "avatar-006",
        "provider": AvatarProvider.HEYGEN,
        "name": "Malik",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.7,
        "preview_url": "https://static.heygen.ai/avatars/avatar-006.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Empathetic business casual presenter",
    },
    {
        "avatar_id": "avatar-007",
        "provider": AvatarProvider.HEYGEN,
        "name": "Omar",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-007.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Professional trustworthy presenter",
    },
    {
        "avatar_id": "avatar-008",
        "provider": AvatarProvider.HEYGEN,
        "name": "Jordan",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "energetic",
        "realism_score": 8.4,
        "preview_url": "https://static.heygen.ai/avatars/avatar-008.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Energetic mixed-background presenter",
    },
    {
        "avatar_id": "avatar-009",
        "provider": AvatarProvider.HEYGEN,
        "name": "Tyler",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 7.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-009.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Everyday relatable young presenter",
    },
    {
        "avatar_id": "avatar-010",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-M-YA-01",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "authoritative",
        "realism_score": 9.2,
        "preview_url": "https://static.tavus.io/replicas/tavus-001.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic young adult male",
    },
    # ── Young Adult Feminine (10) ────────────────────────────────────────────
    {
        "avatar_id": "avatar-011",
        "provider": AvatarProvider.HEYGEN,
        "name": "Sophia",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-011.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Professional authoritative young female presenter",
    },
    {
        "avatar_id": "avatar-012",
        "provider": AvatarProvider.HEYGEN,
        "name": "Aaliyah",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "energetic",
        "realism_score": 8.6,
        "preview_url": "https://static.heygen.ai/avatars/avatar-012.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Energetic casual young female presenter",
    },
    {
        "avatar_id": "avatar-013",
        "provider": AvatarProvider.HEYGEN,
        "name": "Isabella",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "friendly",
        "realism_score": 8.4,
        "preview_url": "https://static.heygen.ai/avatars/avatar-013.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Friendly everyday Latina presenter",
    },
    {
        "avatar_id": "avatar-014",
        "provider": AvatarProvider.HEYGEN,
        "name": "Mei",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-014.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Trustworthy professional East Asian female presenter",
    },
    {
        "avatar_id": "avatar-015",
        "provider": AvatarProvider.HEYGEN,
        "name": "Priya",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.7,
        "preview_url": "https://static.heygen.ai/avatars/avatar-015.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Empathetic South Asian female, business casual",
    },
    {
        "avatar_id": "avatar-016",
        "provider": AvatarProvider.HEYGEN,
        "name": "Zara",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 8.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-016.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Authoritative Middle Eastern female presenter",
    },
    {
        "avatar_id": "avatar-017",
        "provider": AvatarProvider.HEYGEN,
        "name": "Aisha",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "relatable",
        "realism_score": 8.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-017.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Relatable casual young female presenter",
    },
    {
        "avatar_id": "avatar-018",
        "provider": AvatarProvider.HEYGEN,
        "name": "Camila",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "friendly",
        "realism_score": 8.3,
        "preview_url": "https://static.heygen.ai/avatars/avatar-018.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Friendly everyday medium-tone female presenter",
    },
    {
        "avatar_id": "avatar-019",
        "provider": AvatarProvider.HEYGEN,
        "name": "Riley",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "energetic",
        "realism_score": 8.5,
        "preview_url": "https://static.heygen.ai/avatars/avatar-019.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Energetic mixed-background female presenter",
    },
    {
        "avatar_id": "tavus-001",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-F-YA-01",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.YOUNG_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.3,
        "preview_url": "https://static.tavus.io/replicas/tavus-002.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic young adult female",
    },
    # ── Middle-Aged Masculine (10) ───────────────────────────────────────────
    {
        "avatar_id": "avatar-021",
        "provider": AvatarProvider.HEYGEN,
        "name": "Robert",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-021.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Authoritative middle-aged professional male",
    },
    {
        "avatar_id": "avatar-022",
        "provider": AvatarProvider.HEYGEN,
        "name": "James",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-022.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Trustworthy business casual middle-aged male",
    },
    {
        "avatar_id": "avatar-023",
        "provider": AvatarProvider.HEYGEN,
        "name": "Carlos",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "relatable",
        "realism_score": 8.5,
        "preview_url": "https://static.heygen.ai/avatars/avatar-023.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Relatable Latin middle-aged male",
    },
    {
        "avatar_id": "avatar-024",
        "provider": AvatarProvider.HEYGEN,
        "name": "DeShawn",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-024.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Authoritative dark-tone middle-aged professional",
    },
    {
        "avatar_id": "avatar-025",
        "provider": AvatarProvider.HEYGEN,
        "name": "Raj",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.6,
        "preview_url": "https://static.heygen.ai/avatars/avatar-025.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Empathetic South Asian middle-aged presenter",
    },
    {
        "avatar_id": "avatar-026",
        "provider": AvatarProvider.HEYGEN,
        "name": "Kevin",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-026.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Trustworthy East Asian middle-aged professional",
    },
    {
        "avatar_id": "avatar-027",
        "provider": AvatarProvider.HEYGEN,
        "name": "Khalid",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "authoritative",
        "realism_score": 9.2,
        "preview_url": "https://static.heygen.ai/avatars/avatar-027.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Authoritative Middle Eastern middle-aged male",
    },
    {
        "avatar_id": "avatar-028",
        "provider": AvatarProvider.HEYGEN,
        "name": "Marcus Sr.",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 8.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-028.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Relatable everyday middle-aged presenter",
    },
    {
        "avatar_id": "avatar-029",
        "provider": AvatarProvider.HEYGEN,
        "name": "David",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.3,
        "preview_url": "https://static.heygen.ai/avatars/avatar-029.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Friendly casual mixed-background middle-aged male",
    },
    {
        "avatar_id": "tavus-002",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-M-MA-01",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.4,
        "preview_url": "https://static.tavus.io/replicas/tavus-003.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic middle-aged male professional",
    },
    # ── Middle-Aged Feminine (10) ────────────────────────────────────────────
    {
        "avatar_id": "avatar-031",
        "provider": AvatarProvider.HEYGEN,
        "name": "Linda",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-031.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Authoritative professional middle-aged female",
    },
    {
        "avatar_id": "avatar-032",
        "provider": AvatarProvider.HEYGEN,
        "name": "Monique",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.7,
        "preview_url": "https://static.heygen.ai/avatars/avatar-032.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Empathetic dark-tone middle-aged female",
    },
    {
        "avatar_id": "avatar-033",
        "provider": AvatarProvider.HEYGEN,
        "name": "Maria",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.4,
        "preview_url": "https://static.heygen.ai/avatars/avatar-033.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Friendly Latina middle-aged presenter",
    },
    {
        "avatar_id": "avatar-034",
        "provider": AvatarProvider.HEYGEN,
        "name": "Yuki",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-034.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Trustworthy East Asian middle-aged professional female",
    },
    {
        "avatar_id": "avatar-035",
        "provider": AvatarProvider.HEYGEN,
        "name": "Sunita",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "authoritative",
        "realism_score": 8.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-035.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Authoritative South Asian middle-aged female",
    },
    {
        "avatar_id": "avatar-036",
        "provider": AvatarProvider.HEYGEN,
        "name": "Fatima",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-036.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Trustworthy Middle Eastern middle-aged female",
    },
    {
        "avatar_id": "avatar-037",
        "provider": AvatarProvider.HEYGEN,
        "name": "Denise",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 8.2,
        "preview_url": "https://static.heygen.ai/avatars/avatar-037.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Relatable everyday medium-dark middle-aged female",
    },
    {
        "avatar_id": "avatar-038",
        "provider": AvatarProvider.HEYGEN,
        "name": "Karen",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-038.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Friendly casual medium-tone middle-aged female",
    },
    {
        "avatar_id": "avatar-039",
        "provider": AvatarProvider.HEYGEN,
        "name": "Tanya",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.6,
        "preview_url": "https://static.heygen.ai/avatars/avatar-039.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Empathetic mixed-background middle-aged female",
    },
    {
        "avatar_id": "tavus-003",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-F-MA-01",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.MIDDLE_AGED,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.5,
        "preview_url": "https://static.tavus.io/replicas/tavus-004.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic middle-aged female professional",
    },
    # ── Older Adult Masculine (10) ───────────────────────────────────────────
    {
        "avatar_id": "avatar-041",
        "provider": AvatarProvider.HEYGEN,
        "name": "Frank",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-041.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Trustworthy older male casual presenter",
    },
    {
        "avatar_id": "avatar-042",
        "provider": AvatarProvider.HEYGEN,
        "name": "Walter",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-042.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Authoritative older male professional presenter",
    },
    {
        "avatar_id": "avatar-043",
        "provider": AvatarProvider.HEYGEN,
        "name": "Eduardo",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 8.2,
        "preview_url": "https://static.heygen.ai/avatars/avatar-043.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Relatable older Latin male presenter",
    },
    {
        "avatar_id": "avatar-044",
        "provider": AvatarProvider.HEYGEN,
        "name": "Curtis",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.6,
        "preview_url": "https://static.heygen.ai/avatars/avatar-044.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Empathetic dark-tone older male presenter",
    },
    {
        "avatar_id": "avatar-045",
        "provider": AvatarProvider.HEYGEN,
        "name": "Vijay",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 8.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-045.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Authoritative South Asian older male presenter",
    },
    {
        "avatar_id": "avatar-046",
        "provider": AvatarProvider.HEYGEN,
        "name": "Hiroshi",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-046.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Trustworthy East Asian older male presenter",
    },
    {
        "avatar_id": "avatar-047",
        "provider": AvatarProvider.HEYGEN,
        "name": "Hassan",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.4,
        "preview_url": "https://static.heygen.ai/avatars/avatar-047.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Friendly older Middle Eastern male presenter",
    },
    {
        "avatar_id": "avatar-048",
        "provider": AvatarProvider.HEYGEN,
        "name": "Gerald",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 7.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-048.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Relatable everyday older male presenter",
    },
    {
        "avatar_id": "avatar-049",
        "provider": AvatarProvider.HEYGEN,
        "name": "Leonard",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 8.7,
        "preview_url": "https://static.heygen.ai/avatars/avatar-049.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Trustworthy mixed-background older male presenter",
    },
    {
        "avatar_id": "tavus-004",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-M-OA-01",
        "gender_presentation": GenderPresentation.MASCULINE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 9.2,
        "preview_url": "https://static.tavus.io/replicas/tavus-005.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic older adult male",
    },
    # ── Older Adult Feminine (10) ────────────────────────────────────────────
    {
        "avatar_id": "avatar-051",
        "provider": AvatarProvider.HEYGEN,
        "name": "Barbara",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-051.jpg",
        "voice_id": "VR6AewLTigWG4xSOukaG",
        "is_active": True,
        "notes": "Trustworthy older female professional presenter",
    },
    {
        "avatar_id": "avatar-052",
        "provider": AvatarProvider.HEYGEN,
        "name": "Dorothy",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 8.1,
        "preview_url": "https://static.heygen.ai/avatars/avatar-052.jpg",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "is_active": True,
        "notes": "Relatable everyday older female presenter",
    },
    {
        "avatar_id": "avatar-053",
        "provider": AvatarProvider.HEYGEN,
        "name": "Rosa",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LATIN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.3,
        "preview_url": "https://static.heygen.ai/avatars/avatar-053.jpg",
        "voice_id": "yoZ06aMxZJJ28mfd3POQ",
        "is_active": True,
        "notes": "Friendly Latina older female presenter",
    },
    {
        "avatar_id": "avatar-054",
        "provider": AvatarProvider.HEYGEN,
        "name": "Gloria",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.DARK,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "empathetic",
        "realism_score": 8.7,
        "preview_url": "https://static.heygen.ai/avatars/avatar-054.jpg",
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "is_active": True,
        "notes": "Empathetic dark-tone older female presenter",
    },
    {
        "avatar_id": "avatar-055",
        "provider": AvatarProvider.HEYGEN,
        "name": "Meena",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.SOUTH_ASIAN,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 8.9,
        "preview_url": "https://static.heygen.ai/avatars/avatar-055.jpg",
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",
        "is_active": True,
        "notes": "Authoritative South Asian older female presenter",
    },
    {
        "avatar_id": "avatar-056",
        "provider": AvatarProvider.HEYGEN,
        "name": "Akiko",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.EAST_ASIAN,
        "wardrobe_style": WardrobeStyle.BUSINESS_CASUAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.0,
        "preview_url": "https://static.heygen.ai/avatars/avatar-056.jpg",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "is_active": True,
        "notes": "Trustworthy East Asian older female presenter",
    },
    {
        "avatar_id": "avatar-057",
        "provider": AvatarProvider.HEYGEN,
        "name": "Nadia",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MIDDLE_EASTERN,
        "wardrobe_style": WardrobeStyle.CASUAL,
        "tone_persona": "friendly",
        "realism_score": 8.5,
        "preview_url": "https://static.heygen.ai/avatars/avatar-057.jpg",
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "is_active": True,
        "notes": "Friendly older Middle Eastern female presenter",
    },
    {
        "avatar_id": "avatar-058",
        "provider": AvatarProvider.HEYGEN,
        "name": "Evelyn",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MEDIUM_DARK,
        "wardrobe_style": WardrobeStyle.EVERYDAY,
        "tone_persona": "relatable",
        "realism_score": 7.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-058.jpg",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "is_active": True,
        "notes": "Relatable everyday older medium-dark female presenter",
    },
    {
        "avatar_id": "avatar-059",
        "provider": AvatarProvider.HEYGEN,
        "name": "Patricia",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.MIXED,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "authoritative",
        "realism_score": 8.8,
        "preview_url": "https://static.heygen.ai/avatars/avatar-059.jpg",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "is_active": True,
        "notes": "Authoritative mixed-background older female presenter",
    },
    {
        "avatar_id": "tavus-005",
        "provider": AvatarProvider.TAVUS,
        "name": "Tavus-F-OA-01",
        "gender_presentation": GenderPresentation.FEMININE,
        "age_group": AgeGroup.OLDER_ADULT,
        "appearance_tag": AppearanceTag.LIGHT,
        "wardrobe_style": WardrobeStyle.PROFESSIONAL,
        "tone_persona": "trustworthy",
        "realism_score": 9.3,
        "preview_url": "https://static.tavus.io/replicas/tavus-006.jpg",
        "voice_id": None,
        "is_active": True,
        "notes": "Tavus photorealistic older adult female",
    },
]

# ---------------------------------------------------------------------------
# Default diversity quotas (percentages → raw counts computed at call time)
# ---------------------------------------------------------------------------

_DEFAULT_QUOTA_FRACTIONS: Dict[str, float] = {
    "middle_aged_masculine": 0.20,
    "middle_aged_feminine": 0.20,
    "older_adult_masculine": 0.17,
    "older_adult_feminine": 0.17,
    "young_adult_masculine": 0.13,
    "young_adult_feminine": 0.13,
}


def _avatar_group_key(avatar: AvatarMetadata) -> str:
    """Return a stable group key for quota bucketing."""
    age = avatar.age_group if isinstance(avatar.age_group, str) else avatar.age_group.value
    gender = avatar.gender_presentation if isinstance(avatar.gender_presentation, str) else avatar.gender_presentation.value
    return f"{age}_{gender}"


# ---------------------------------------------------------------------------
# AvatarCatalogAgent
# ---------------------------------------------------------------------------

class AvatarCatalogAgent:
    """
    Manages a catalog of AI avatar personas.

    On first use the built-in catalog of 60 entries is written to disk.
    Subsequent runs load from disk and optionally sync new avatars from the provider.
    """

    BUILTIN_CATALOG: List[Dict[str, Any]] = _BUILTIN_CATALOG

    def __init__(self, config: AppConfig, provider: BaseAvatarProvider) -> None:
        self.config = config
        self.provider = provider
        self.catalog_path = Path(config.avatar_selection.catalog_path)
        self._cache: Optional[List[AvatarMetadata]] = None
        logger.debug("AvatarCatalogAgent initialized. catalog_path=%s", self.catalog_path)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load_catalog(self) -> List[AvatarMetadata]:
        """Load catalog from disk. Seeds from built-in catalog on first run."""
        if not self.catalog_path.exists():
            logger.info("Catalog file not found — seeding from built-in catalog (%d entries)", len(self.BUILTIN_CATALOG))
            avatars = self._builtin_to_metadata()
            self.save_catalog(avatars)
            return avatars

        try:
            avatars = read_models_json(self.catalog_path, AvatarMetadata)
            logger.info("Loaded %d avatars from catalog: %s", len(avatars), self.catalog_path)
            return avatars
        except Exception as exc:
            logger.warning("Failed to load catalog (%s) — falling back to built-in: %s", self.catalog_path, exc)
            return self._builtin_to_metadata()

    def save_catalog(self, avatars: List[AvatarMetadata]) -> None:
        """Persist avatar list to catalog JSON file."""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        write_models_json(avatars, self.catalog_path)
        logger.info("Saved %d avatars to %s", len(avatars), self.catalog_path)
        self._cache = avatars

    def _builtin_to_metadata(self) -> List[AvatarMetadata]:
        """Convert built-in catalog dicts to AvatarMetadata objects."""
        result: List[AvatarMetadata] = []
        now = datetime.utcnow()
        for entry in self.BUILTIN_CATALOG:
            try:
                meta = AvatarMetadata(
                    synced_at=now,
                    **{k: v for k, v in entry.items()},
                )
                result.append(meta)
            except Exception as exc:
                logger.warning("Failed to parse built-in catalog entry %s: %s", entry.get("avatar_id"), exc)
        return result

    # ------------------------------------------------------------------
    # Provider sync
    # ------------------------------------------------------------------

    def sync_from_provider(self) -> int:
        """
        Fetch avatars from the provider API and merge new entries into the catalog.
        Returns the count of newly added avatars.
        """
        logger.info("Syncing avatars from provider...")
        existing = self.get_all()
        existing_ids = {a.avatar_id for a in existing}

        try:
            raw_list = self.provider.list_avatars()
        except Exception as exc:
            logger.error("Provider list_avatars() failed: %s", exc)
            return 0

        added = 0
        now = datetime.utcnow()
        for raw in raw_list:
            avatar_id = (
                raw.get("avatar_id")
                or raw.get("id")
                or raw.get("replica_id")
                or ""
            )
            if not avatar_id or avatar_id in existing_ids:
                continue

            try:
                meta = self._map_provider_avatar(raw, now)
                existing.append(meta)
                existing_ids.add(avatar_id)
                added += 1
            except Exception as exc:
                logger.warning("Skipping provider avatar %s: %s", avatar_id, exc)

        if added > 0:
            self.save_catalog(existing)
            logger.info("Synced %d new avatar(s) from provider", added)
        else:
            logger.info("No new avatars from provider (catalog already up to date)")

        return added

    def _map_provider_avatar(self, raw: Dict[str, Any], synced_at: datetime) -> AvatarMetadata:
        """Map a raw provider response dict to AvatarMetadata using best-effort field mapping."""
        avatar_id = (
            raw.get("avatar_id")
            or raw.get("id")
            or raw.get("replica_id")
            or ""
        )
        name = (
            raw.get("avatar_name")
            or raw.get("name")
            or raw.get("replica_name")
            or avatar_id
        )
        preview_url = (
            raw.get("preview_image_url")
            or raw.get("preview_url")
            or raw.get("thumbnail_url")
            or None
        )

        # Best-effort gender detection from name or tags
        gender = GenderPresentation.NEUTRAL
        gender_hint = str(raw.get("gender") or raw.get("tags") or "").lower()
        if any(w in gender_hint for w in ("female", "feminine", "woman", "girl", "f")):
            gender = GenderPresentation.FEMININE
        elif any(w in gender_hint for w in ("male", "masculine", "man", "boy", "m")):
            gender = GenderPresentation.MASCULINE

        return AvatarMetadata(
            avatar_id=avatar_id,
            provider=self.config.providers.avatar.provider,
            name=name,
            gender_presentation=gender,
            age_group=AgeGroup.MIDDLE_AGED,
            appearance_tag=AppearanceTag.MEDIUM,
            wardrobe_style=WardrobeStyle.CASUAL,
            tone_persona="friendly",
            realism_score=float(raw.get("realism_score", 8.0)),
            preview_url=preview_url,
            voice_id=raw.get("voice_id") or raw.get("default_voice_id") or None,
            is_active=True,
            notes=f"Synced from provider at {synced_at.isoformat()}",
            synced_at=synced_at,
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_all(self) -> List[AvatarMetadata]:
        """Return all active avatars, loading from disk if needed."""
        if self._cache is None:
            self._cache = self.load_catalog()
        return [a for a in self._cache if a.is_active]

    def get_by_id(self, avatar_id: str) -> Optional[AvatarMetadata]:
        """Find an avatar by provider avatar_id."""
        for avatar in self.get_all():
            if avatar.avatar_id == avatar_id:
                return avatar
        return None

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_by(
        self,
        age_group: Optional[str] = None,
        gender: Optional[str] = None,
        appearance_tag: Optional[str] = None,
        wardrobe: Optional[str] = None,
        min_realism: float = 7.0,
    ) -> List[AvatarMetadata]:
        """Return avatars matching all provided filter criteria."""
        results = self.get_all()

        if min_realism > 0:
            results = [a for a in results if a.realism_score >= min_realism]

        if age_group is not None:
            results = [
                a for a in results
                if (a.age_group if isinstance(a.age_group, str) else a.age_group.value) == age_group
            ]

        if gender is not None:
            results = [
                a for a in results
                if (a.gender_presentation if isinstance(a.gender_presentation, str) else a.gender_presentation.value) == gender
            ]

        if appearance_tag is not None:
            results = [
                a for a in results
                if (a.appearance_tag if isinstance(a.appearance_tag, str) else a.appearance_tag.value) == appearance_tag
            ]

        if wardrobe is not None:
            results = [
                a for a in results
                if (a.wardrobe_style if isinstance(a.wardrobe_style, str) else a.wardrobe_style.value) == wardrobe
            ]

        return results

    # ------------------------------------------------------------------
    # Batch selection
    # ------------------------------------------------------------------

    def select_balanced_batch(
        self,
        count: int,
        quotas: Optional[Dict[str, int]] = None,
    ) -> List[AvatarMetadata]:
        """
        Select `count` avatars with diversity quotas.

        Default quota fractions:
            middle_aged_masculine=20%, middle_aged_feminine=20%,
            older_adult_masculine=17%, older_adult_feminine=17%,
            young_adult_masculine=13%, young_adult_feminine=13%

        No single avatar appears more than config.avatar_selection.max_reuse_per_batch times.
        """
        all_avatars = self.get_all()
        max_reuse = self.config.avatar_selection.max_reuse_per_batch

        # Build group buckets
        groups: Dict[str, List[AvatarMetadata]] = {}
        for avatar in all_avatars:
            key = _avatar_group_key(avatar)
            groups.setdefault(key, [])
            groups[key].append(avatar)

        # Shuffle within each group for randomness
        for grp in groups.values():
            random.shuffle(grp)

        # Determine per-group counts
        if quotas is not None:
            group_counts = {k: v for k, v in quotas.items()}
        else:
            group_counts = {
                key: max(1, int(frac * count))
                for key, frac in _DEFAULT_QUOTA_FRACTIONS.items()
            }

        # Fill from each group respecting max_reuse
        selected: List[AvatarMetadata] = []
        reuse_counter: Dict[str, int] = {}

        for group_key, target_count in group_counts.items():
            bucket = groups.get(group_key, [])
            added = 0
            idx = 0
            while added < target_count and len(selected) < count:
                if idx >= len(bucket):
                    break
                avatar = bucket[idx]
                idx += 1
                uses = reuse_counter.get(avatar.avatar_id, 0)
                if uses < max_reuse:
                    selected.append(avatar)
                    reuse_counter[avatar.avatar_id] = uses + 1
                    added += 1

        # If we still need more avatars, fill remaining from any group
        if len(selected) < count:
            remaining_pool = [
                a for a in all_avatars
                if reuse_counter.get(a.avatar_id, 0) < max_reuse
            ]
            random.shuffle(remaining_pool)
            for avatar in remaining_pool:
                if len(selected) >= count:
                    break
                uses = reuse_counter.get(avatar.avatar_id, 0)
                if uses < max_reuse:
                    selected.append(avatar)
                    reuse_counter[avatar.avatar_id] = uses + 1

        random.shuffle(selected)
        logger.info("select_balanced_batch: requested=%d selected=%d", count, len(selected))
        return selected[:count]

    def select_random(
        self,
        count: int,
        seed: Optional[int] = None,
    ) -> List[AvatarMetadata]:
        """Select `count` random avatars, optionally with a fixed seed for reproducibility."""
        all_avatars = self.get_all()
        rng = random.Random(seed) if seed is not None else random
        pool = list(all_avatars)
        rng.shuffle(pool)
        selected = pool[:count]
        logger.info("select_random: requested=%d selected=%d (seed=%s)", count, len(selected), seed)
        return selected
