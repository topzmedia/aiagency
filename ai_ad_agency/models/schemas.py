"""
Pydantic schemas / data models for the AI Ad Agency platform.
All shared data structures live here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .enums import (
    AgeGroup,
    AppearanceTag,
    AssetStatus,
    AvatarProvider,
    CreativeType,
    GenderPresentation,
    HookCategory,
    ImageProvider,
    ImageStyle,
    LLMProvider,
    RenderStatus,
    ScriptStyle,
    VideoLength,
    VideoProvider,
    VoiceProvider,
    VoiceTone,
    WardrobeStyle,
)


def _gen_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Offer Config
# ---------------------------------------------------------------------------

class OfferConfig(BaseModel):
    offer_name: str
    offer_description: str
    vertical: str
    target_audience: str
    pain_points: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    cta: str = "Learn More"
    landing_page: str = ""
    tone: List[str] = Field(default_factory=list)
    hook_categories: List[HookCategory] = Field(
        default_factory=lambda: list(HookCategory)
    )
    script_styles: List[ScriptStyle] = Field(
        default_factory=lambda: list(ScriptStyle)
    )
    video_lengths: List[VideoLength] = Field(
        default_factory=lambda: list(VideoLength)
    )
    image_styles: List[ImageStyle] = Field(
        default_factory=lambda: list(ImageStyle)
    )
    broll_themes: List[str] = Field(default_factory=list)
    brand_name: str = ""
    brand_colors: List[str] = Field(default_factory=list)
    disclaimer_text: str = ""

    @field_validator("hook_categories", mode="before")
    @classmethod
    def coerce_hook_categories(cls, v: Any) -> List[HookCategory]:
        return [HookCategory(x) if isinstance(x, str) else x for x in v]

    @field_validator("script_styles", mode="before")
    @classmethod
    def coerce_script_styles(cls, v: Any) -> List[ScriptStyle]:
        return [ScriptStyle(x) if isinstance(x, str) else x for x in v]

    @field_validator("video_lengths", mode="before")
    @classmethod
    def coerce_video_lengths(cls, v: Any) -> List[VideoLength]:
        return [VideoLength(x) if isinstance(x, str) else x for x in v]

    @field_validator("image_styles", mode="before")
    @classmethod
    def coerce_image_styles(cls, v: Any) -> List[ImageStyle]:
        return [ImageStyle(x) if isinstance(x, str) else x for x in v]


# ---------------------------------------------------------------------------
# Hook Models
# ---------------------------------------------------------------------------

class Hook(BaseModel):
    hook_id: str = Field(default_factory=_gen_id)
    text: str
    category: HookCategory
    strength_score: float = 0.0
    offer_name: str = ""
    word_count: int = 0
    char_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.COMPLETED

    def model_post_init(self, __context: Any) -> None:
        if self.word_count == 0:
            self.word_count = len(self.text.split())
        if self.char_count == 0:
            self.char_count = len(self.text)


class RotatedHook(BaseModel):
    rotated_id: str = Field(default_factory=_gen_id)
    parent_hook_id: str
    text: str
    similarity_score: float = 0.0  # Lower is more diverse
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.COMPLETED


# ---------------------------------------------------------------------------
# Script Models
# ---------------------------------------------------------------------------

class ScriptSection(BaseModel):
    hook: str
    problem: str
    discovery: str
    benefit: str
    cta: str


class Script(BaseModel):
    script_id: str = Field(default_factory=_gen_id)
    hook_id: str
    rotated_hook_id: Optional[str] = None
    hook_text: str
    style: ScriptStyle
    length: VideoLength
    sections: ScriptSection
    full_text: str
    voice_safe_text: str  # Stripped of special chars, normalized for TTS
    estimated_duration_sec: int
    word_count: int = 0
    tags: List[str] = Field(default_factory=list)
    offer_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.COMPLETED

    def model_post_init(self, __context: Any) -> None:
        if self.word_count == 0:
            self.word_count = len(self.full_text.split())


class ScriptVariant(BaseModel):
    variant_id: str = Field(default_factory=_gen_id)
    parent_script_id: str
    hook_id: str
    style: ScriptStyle
    length: VideoLength
    sections: ScriptSection
    full_text: str
    voice_safe_text: str
    estimated_duration_sec: int
    variation_note: str = ""  # e.g. "alternate intro", "softer CTA"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.COMPLETED


# ---------------------------------------------------------------------------
# Avatar Models
# ---------------------------------------------------------------------------

class AvatarMetadata(BaseModel):
    avatar_id: str  # Provider's ID or internal ID
    internal_id: str = Field(default_factory=_gen_id)
    provider: AvatarProvider
    name: str = ""
    gender_presentation: GenderPresentation = GenderPresentation.NEUTRAL
    age_group: AgeGroup = AgeGroup.MIDDLE_AGED
    appearance_tag: AppearanceTag = AppearanceTag.MEDIUM
    wardrobe_style: WardrobeStyle = WardrobeStyle.CASUAL
    tone_persona: str = "neutral"
    realism_score: float = 8.0  # 1-10
    preview_url: Optional[str] = None
    voice_id: Optional[str] = None  # Default voice for this avatar
    is_active: bool = True
    notes: str = ""
    synced_at: Optional[datetime] = None

    model_config = {"use_enum_values": True}


# ---------------------------------------------------------------------------
# Voice Models
# ---------------------------------------------------------------------------

class VoiceProfile(BaseModel):
    voice_id: str
    internal_id: str = Field(default_factory=_gen_id)
    provider: VoiceProvider
    name: str
    tone: VoiceTone = VoiceTone.CONVERSATIONAL
    gender: GenderPresentation = GenderPresentation.NEUTRAL
    language: str = "en-US"
    accent: str = ""
    preview_url: Optional[str] = None
    is_active: bool = True


class GeneratedVoice(BaseModel):
    voice_asset_id: str = Field(default_factory=_gen_id)
    voice_profile_id: str
    script_id: str
    file_path: str
    duration_sec: float
    provider: VoiceProvider
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.PENDING
    file_size_bytes: int = 0


# ---------------------------------------------------------------------------
# Image Models
# ---------------------------------------------------------------------------

class ImageCreative(BaseModel):
    image_id: str = Field(default_factory=_gen_id)
    offer_name: str
    style: ImageStyle
    prompt: str
    file_path: str
    width: int
    height: int
    file_size_bytes: int = 0
    provider: ImageProvider = ImageProvider.OPENAI_DALLE
    hook_id: Optional[str] = None
    headline_text: Optional[str] = None
    cta_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.PENDING


# ---------------------------------------------------------------------------
# B-Roll Models
# ---------------------------------------------------------------------------

class BRollClip(BaseModel):
    broll_id: str = Field(default_factory=_gen_id)
    theme: str
    prompt: str
    file_path: str
    duration_sec: float
    width: int
    height: int
    file_size_bytes: int = 0
    provider: VideoProvider = VideoProvider.MOCK
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.PENDING


# ---------------------------------------------------------------------------
# Caption / Overlay Models
# ---------------------------------------------------------------------------

class CaptionLine(BaseModel):
    index: int
    start_sec: float
    end_sec: float
    text: str


class CaptionFile(BaseModel):
    caption_id: str = Field(default_factory=_gen_id)
    script_id: str
    srt_path: str
    json_path: str
    lines: List[CaptionLine] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Overlay(BaseModel):
    overlay_id: str = Field(default_factory=_gen_id)
    overlay_type: str  # "hook_card", "cta_end", "lower_third"
    text: str
    file_path: Optional[str] = None  # Pre-rendered image if applicable
    duration_sec: float = 2.0
    position: str = "top"  # top, bottom, center
    font_size: int = 48
    font_color: str = "white"
    bg_color: str = "#00000088"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Talking Actor Job
# ---------------------------------------------------------------------------

class TalkingActorJob(BaseModel):
    job_id: str = Field(default_factory=_gen_id)
    avatar_id: str
    avatar_provider: AvatarProvider
    script_id: str
    voice_safe_text: str
    voice_id: Optional[str] = None
    provider_job_id: Optional[str] = None
    render_status: RenderStatus = RenderStatus.QUEUED
    file_path: Optional[str] = None
    duration_sec: Optional[float] = None
    width: int = 1080
    height: int = 1920
    attempts: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    file_size_bytes: int = 0


# ---------------------------------------------------------------------------
# Final Creative / Variant
# ---------------------------------------------------------------------------

class CreativeVariant(BaseModel):
    creative_id: str = Field(default_factory=_gen_id)
    run_id: str
    creative_type: CreativeType

    # Lineage
    hook_id: Optional[str] = None
    rotated_hook_id: Optional[str] = None
    script_id: Optional[str] = None
    script_variant_id: Optional[str] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None
    broll_ids: List[str] = Field(default_factory=list)
    caption_id: Optional[str] = None
    overlay_ids: List[str] = Field(default_factory=list)
    image_id: Optional[str] = None

    # Output
    file_path: Optional[str] = None
    width: int = 0
    height: int = 0
    duration_sec: Optional[float] = None
    file_size_bytes: int = 0

    # QA / Scoring
    status: AssetStatus = AssetStatus.PENDING
    qa_passed: bool = False
    qa_notes: List[str] = Field(default_factory=list)
    score: float = 0.0
    content_hash: Optional[str] = None

    # Meta
    hook_text: Optional[str] = None
    offer_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    exported_at: Optional[datetime] = None
    export_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Run Manifest
# ---------------------------------------------------------------------------

class RunManifest(BaseModel):
    run_id: str = Field(default_factory=_gen_id)
    offer_name: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Counts
    hooks_generated: int = 0
    rotated_hooks_generated: int = 0
    scripts_generated: int = 0
    script_variants_generated: int = 0
    images_generated: int = 0
    broll_clips_generated: int = 0
    talking_actor_jobs: int = 0
    variants_planned: int = 0
    variants_rendered: int = 0
    variants_accepted: int = 0
    variants_rejected: int = 0

    # Paths
    output_dir: str = ""
    export_dir: str = ""
    log_path: str = ""

    # Status
    status: AssetStatus = AssetStatus.PENDING
    error: Optional[str] = None

    # Config snapshot
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# QA Result
# ---------------------------------------------------------------------------

class QAResult(BaseModel):
    asset_id: str
    asset_type: str
    file_path: str
    passed: bool
    issues: List[str] = Field(default_factory=list)
    file_exists: bool = False
    file_size_bytes: int = 0
    duration_sec: Optional[float] = None
    has_audio: Optional[bool] = None
    width: Optional[int] = None
    height: Optional[int] = None
    content_hash: Optional[str] = None
    is_duplicate: bool = False
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Export Record
# ---------------------------------------------------------------------------

class ExportRecord(BaseModel):
    export_id: str = Field(default_factory=_gen_id)
    run_id: str
    creative_id: str
    source_path: str
    export_path: str
    creative_type: CreativeType
    hook_text: Optional[str] = None
    script_id: Optional[str] = None
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None
    broll_ids: List[str] = Field(default_factory=list)
    duration_sec: Optional[float] = None
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    score: float = 0.0
    qa_notes: List[str] = Field(default_factory=list)
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    status: AssetStatus = AssetStatus.ACCEPTED
