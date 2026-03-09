"""ASR (Automatic Speech Recognition) / transcription service.

Provides a provider interface and a faster-whisper implementation for
transcribing audio extracted from candidate videos.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TranscriptChunk:
    """A timed segment of transcribed speech."""
    start_sec: float
    end_sec: float
    text: str


@dataclass
class TranscriptResult:
    """Complete transcription result."""
    full_text: str
    chunks: list[TranscriptChunk] = field(default_factory=list)
    language: str | None = None
    language_probability: float | None = None


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class ASRProvider(abc.ABC):
    """Abstract ASR provider."""

    @abc.abstractmethod
    def transcribe(self, audio_path: str | Path) -> TranscriptResult:
        """Transcribe an audio file and return timestamped results."""
        ...


# ---------------------------------------------------------------------------
# faster-whisper implementation (lazy-loaded)
# ---------------------------------------------------------------------------

class FasterWhisperProvider(ASRProvider):
    """ASR provider using faster-whisper (CTranslate2-based Whisper)."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # type: ignore[import-untyped]
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info(
                    "faster-whisper model loaded (size=%s, device=%s)",
                    self._model_size, self._device,
                )
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is required for FasterWhisperProvider. "
                    "Install with: pip install faster-whisper"
                )
        return self._model

    def transcribe(self, audio_path: str | Path) -> TranscriptResult:
        model = self._get_model()
        audio_path = str(audio_path)

        try:
            segments_iter, info = model.transcribe(
                audio_path,
                beam_size=5,
                vad_filter=True,
            )
        except Exception:
            logger.exception("faster-whisper transcription failed for %s", audio_path)
            return TranscriptResult(full_text="")

        chunks: list[TranscriptChunk] = []
        text_parts: list[str] = []

        for segment in segments_iter:
            chunk = TranscriptChunk(
                start_sec=round(segment.start, 3),
                end_sec=round(segment.end, 3),
                text=segment.text.strip(),
            )
            chunks.append(chunk)
            text_parts.append(chunk.text)

        full_text = " ".join(text_parts)

        result = TranscriptResult(
            full_text=full_text,
            chunks=chunks,
            language=info.language if info else None,
            language_probability=round(info.language_probability, 4) if info else None,
        )

        logger.info(
            "Transcribed %s: %d chunks, %d chars, lang=%s",
            audio_path, len(chunks), len(full_text), result.language,
        )
        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_asr_provider(
    provider_name: str = "faster-whisper",
    model_size: str = "base",
) -> ASRProvider:
    """Factory function to get an ASR provider by name."""
    if provider_name == "faster-whisper":
        return FasterWhisperProvider(model_size=model_size)
    raise ValueError(f"Unknown ASR provider: {provider_name}")
