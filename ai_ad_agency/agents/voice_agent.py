"""
Voice Agent — manages voice synthesis and voice profile catalog.
Generates audio when the avatar provider doesn't handle voice natively.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.enums import AssetStatus, GenderPresentation, VoiceTone
from ..models.schemas import (
    AvatarMetadata,
    GeneratedVoice,
    Script,
    ScriptVariant,
    VoiceProfile,
)
from ..utils.config import AppConfig
from ..utils.io import get_file_size, write_models_json, models_to_csv
from ..utils.logging_utils import get_module_logger
from ..models.enums import VoiceProvider

logger = get_module_logger("voice_agent")


# Built-in voice profile stubs for ElevenLabs
_BUILTIN_ELEVENLABS_VOICES = [
    VoiceProfile(
        voice_id="21m00Tcm4TlvDq8ikWAM",
        provider=VoiceProvider.ELEVENLABS,
        name="Rachel",
        tone=VoiceTone.CALM,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="AZnzlk1XvdvUeBnXmlld",
        provider=VoiceProvider.ELEVENLABS,
        name="Domi",
        tone=VoiceTone.ENERGETIC,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        provider=VoiceProvider.ELEVENLABS,
        name="Bella",
        tone=VoiceTone.WARM,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="ErXwobaYiN019PkySvjV",
        provider=VoiceProvider.ELEVENLABS,
        name="Antoni",
        tone=VoiceTone.CONVERSATIONAL,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="MF3mGyEYCl7XYWbV9V6O",
        provider=VoiceProvider.ELEVENLABS,
        name="Elli",
        tone=VoiceTone.TESTIMONIAL,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="TxGEqnHWrfWFTfGW9XjX",
        provider=VoiceProvider.ELEVENLABS,
        name="Josh",
        tone=VoiceTone.CONVERSATIONAL,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="VR6AewLTigWG4xSOukaG",
        provider=VoiceProvider.ELEVENLABS,
        name="Arnold",
        tone=VoiceTone.AUTHORITATIVE,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="pNInz6obpgDQGcFmaJgB",
        provider=VoiceProvider.ELEVENLABS,
        name="Adam",
        tone=VoiceTone.AUTHORITATIVE,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="yoZ06aMxZJJ28mfd3POQ",
        provider=VoiceProvider.ELEVENLABS,
        name="Sam",
        tone=VoiceTone.CONVERSATIONAL,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="jBpfuIE2acCO8z3wKNLl",
        provider=VoiceProvider.ELEVENLABS,
        name="Gigi",
        tone=VoiceTone.WARM,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="American",
    ),
    VoiceProfile(
        voice_id="t0jbNlBVZ17f02VDIeMI",
        provider=VoiceProvider.ELEVENLABS,
        name="Serena",
        tone=VoiceTone.CALM,
        gender=GenderPresentation.FEMININE,
        language="en-US",
        accent="British",
    ),
    VoiceProfile(
        voice_id="onwK4e9ZLuTAKqWW03F9",
        provider=VoiceProvider.ELEVENLABS,
        name="Daniel",
        tone=VoiceTone.AUTHORITATIVE,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
        accent="British",
    ),
]

# Built-in OpenAI TTS voices
_BUILTIN_OPENAI_VOICES = [
    VoiceProfile(
        voice_id="alloy",
        provider=VoiceProvider.OPENAI_TTS,
        name="Alloy",
        tone=VoiceTone.CONVERSATIONAL,
        gender=GenderPresentation.NEUTRAL,
        language="en-US",
    ),
    VoiceProfile(
        voice_id="echo",
        provider=VoiceProvider.OPENAI_TTS,
        name="Echo",
        tone=VoiceTone.WARM,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
    ),
    VoiceProfile(
        voice_id="fable",
        provider=VoiceProvider.OPENAI_TTS,
        name="Fable",
        tone=VoiceTone.ENERGETIC,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
    ),
    VoiceProfile(
        voice_id="onyx",
        provider=VoiceProvider.OPENAI_TTS,
        name="Onyx",
        tone=VoiceTone.AUTHORITATIVE,
        gender=GenderPresentation.MASCULINE,
        language="en-US",
    ),
    VoiceProfile(
        voice_id="nova",
        provider=VoiceProvider.OPENAI_TTS,
        name="Nova",
        tone=VoiceTone.CALM,
        gender=GenderPresentation.FEMININE,
        language="en-US",
    ),
    VoiceProfile(
        voice_id="shimmer",
        provider=VoiceProvider.OPENAI_TTS,
        name="Shimmer",
        tone=VoiceTone.TESTIMONIAL,
        gender=GenderPresentation.FEMININE,
        language="en-US",
    ),
]

_BUILTIN_MOCK_VOICES = [
    VoiceProfile(
        voice_id=f"mock_voice_{i:03d}",
        provider=VoiceProvider.MOCK,
        name=f"MockVoice_{i:03d}",
        tone=list(VoiceTone)[i % len(VoiceTone)],
        gender=[GenderPresentation.MASCULINE, GenderPresentation.FEMININE][i % 2],
        language="en-US",
    )
    for i in range(1, 13)
]


class VoiceAgent:
    """
    Manages voice synthesis and voice profile catalog.
    Used when talking actor providers don't handle voice natively,
    or when generating standalone audio assets.
    """

    def __init__(self, config: AppConfig, provider: object):
        from ..providers.voice_provider import BaseVoiceProvider
        self.config = config
        self.provider: BaseVoiceProvider = provider  # type: ignore
        self._profiles: List[VoiceProfile] = []

    def sync_voices(self) -> List[VoiceProfile]:
        """
        Fetch voices from provider and merge with built-in catalog.
        Returns unified list of VoiceProfile.
        """
        provider_voices = []
        try:
            raw = self.provider.list_voices()
            for v in raw:
                try:
                    profile = VoiceProfile(
                        voice_id=v.get("voice_id", "") or v.get("id", ""),
                        provider=self.config.providers.voice.provider,
                        name=v.get("name", "Unknown"),
                        tone=VoiceTone.CONVERSATIONAL,
                        language="en-US",
                    )
                    if profile.voice_id:
                        provider_voices.append(profile)
                except Exception as e:
                    logger.debug("Skipping voice entry: %s", e)
        except Exception as e:
            logger.warning("Could not fetch voices from provider: %s", e)

        # Use built-ins as fallback / supplement
        builtin = self._get_builtin_profiles()
        existing_ids = {v.voice_id for v in provider_voices}
        combined = list(provider_voices)
        for v in builtin:
            if v.voice_id not in existing_ids:
                combined.append(v)

        self._profiles = combined
        logger.info("Voice catalog: %d profiles (%d from provider)", len(combined), len(provider_voices))
        return combined

    def _get_builtin_profiles(self) -> List[VoiceProfile]:
        prov = self.config.providers.voice.provider
        if str(prov) in ("elevenlabs", VoiceProvider.ELEVENLABS):
            return _BUILTIN_ELEVENLABS_VOICES
        elif str(prov) in ("openai_tts", VoiceProvider.OPENAI_TTS):
            return _BUILTIN_OPENAI_VOICES
        else:
            return _BUILTIN_MOCK_VOICES

    def generate_voice(
        self,
        text: str,
        voice_profile: VoiceProfile,
        output_path: str,
    ) -> Optional[GeneratedVoice]:
        """Synthesize speech for a text string. Returns GeneratedVoice or None on failure."""
        from ..utils.io import get_file_size
        from ..utils.ffmpeg_utils import get_duration

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        ok = self.provider.synthesize(
            text=text,
            voice_id=voice_profile.voice_id,
            output_path=output_path,
            tone=voice_profile.tone,
        )
        if not ok:
            return None

        size = get_file_size(output_path)
        duration = get_duration(output_path) or 0.0

        return GeneratedVoice(
            voice_profile_id=voice_profile.internal_id,
            script_id="",
            file_path=output_path,
            duration_sec=duration,
            provider=voice_profile.provider,
            file_size_bytes=size,
            status=AssetStatus.COMPLETED,
        )

    def generate_batch(
        self,
        scripts: List[Union[Script, ScriptVariant]],
        voice_profiles: List[VoiceProfile],
        output_dir: str,
    ) -> List[GeneratedVoice]:
        """Generate voice for each script, cycling through available profiles."""
        if not voice_profiles:
            voice_profiles = self.sync_voices()
        if not voice_profiles:
            logger.error("No voice profiles available")
            return []

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results: List[GeneratedVoice] = []
        n_profiles = len(voice_profiles)

        for i, script in enumerate(scripts):
            profile = voice_profiles[i % n_profiles]
            script_id = getattr(script, "script_id", None) or getattr(script, "variant_id", f"script_{i}")

            # Check cache
            cached = self.get_cached_voice(script_id, profile.voice_id, output_dir)
            if cached:
                logger.debug("Using cached voice for script %s", script_id[:8])
                continue

            out_path = str(Path(output_dir) / f"voice_{script_id[:12]}_{profile.voice_id[:8]}.mp3")
            generated = self.generate_voice(
                text=script.voice_safe_text,
                voice_profile=profile,
                output_path=out_path,
            )
            if generated:
                generated.script_id = script_id
                results.append(generated)
                if (i + 1) % 10 == 0:
                    logger.info("Generated %d/%d voice clips", i + 1, len(scripts))
            else:
                logger.warning("Voice generation failed for script %s", script_id[:8])

        logger.info("Voice batch complete: %d/%d generated", len(results), len(scripts))
        return results

    def select_voice_for_avatar(
        self,
        avatar: AvatarMetadata,
        available_profiles: List[VoiceProfile],
    ) -> Optional[VoiceProfile]:
        """
        Select the best matching voice for an avatar based on gender.
        Falls back to any available voice.
        """
        if not available_profiles:
            return None

        # Try gender match
        gender_matches = [
            p for p in available_profiles
            if p.gender == avatar.gender_presentation
        ]
        if gender_matches:
            import random
            return random.choice(gender_matches)

        # Fallback: any voice
        import random
        return random.choice(available_profiles)

    def get_cached_voice(
        self,
        script_id: str,
        voice_id: str,
        output_dir: str,
    ) -> Optional[str]:
        """Check if a voice file already exists for this script+voice combo."""
        expected = Path(output_dir) / f"voice_{script_id[:12]}_{voice_id[:8]}.mp3"
        if expected.exists() and expected.stat().st_size > 100:
            return str(expected)
        return None

    def save_profiles(self, profiles: List[VoiceProfile], output_dir: str) -> None:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        write_models_json(profiles, str(Path(output_dir) / "voice_profiles.json"))
        models_to_csv(profiles, str(Path(output_dir) / "voice_profiles.csv"))
