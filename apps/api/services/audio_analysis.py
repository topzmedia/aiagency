"""Audio event analysis service.

Provides keyword-based and basic amplitude heuristic analysis of audio tracks
to detect events like impacts, barking, cheering, etc.
"""
from __future__ import annotations

import abc
import logging
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AudioEvent:
    """A detected audio event."""
    label: str
    confidence: float
    timestamp: float | None = None


# ---------------------------------------------------------------------------
# Audio event labels
# ---------------------------------------------------------------------------

AUDIO_LABELS = [
    "impact", "screech", "bark", "thunder", "cheering",
    "crying", "music", "silence", "speech",
]


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class AudioAnalyzer(abc.ABC):
    """Abstract audio analysis interface."""

    @abc.abstractmethod
    def analyze(
        self,
        audio_path: str | Path,
        transcript: str | None = None,
    ) -> list[AudioEvent]:
        """Analyze an audio track and return detected events."""
        ...


# ---------------------------------------------------------------------------
# Keyword + amplitude heuristic implementation
# ---------------------------------------------------------------------------

# Transcript keyword -> audio event mapping
_TRANSCRIPT_AUDIO_MAP: dict[str, list[str]] = {
    "impact": ["crash", "bang", "boom", "impact", "smash", "hit", "collision"],
    "screech": ["screech", "skid", "brake", "squeal", "tire"],
    "bark": ["bark", "woof", "dog", "puppy", "growl"],
    "thunder": ["thunder", "storm", "lightning", "rumble"],
    "cheering": ["cheer", "crowd", "applause", "hooray", "yeah", "woo"],
    "crying": ["cry", "sob", "weep", "tear", "boo hoo"],
    "music": ["music", "song", "sing", "melody", "beat", "rhythm"],
    "speech": ["said", "told", "talk", "speak", "say", "voice", "conversation"],
}


def _analyze_transcript_keywords(transcript: str) -> list[AudioEvent]:
    """Detect audio events from transcript keywords."""
    transcript_lower = transcript.lower()
    events: list[AudioEvent] = []

    for label, keywords in _TRANSCRIPT_AUDIO_MAP.items():
        matches = [kw for kw in keywords if kw in transcript_lower]
        if matches:
            confidence = min(0.8, 0.3 + len(matches) * 0.12)
            events.append(AudioEvent(
                label=label,
                confidence=round(confidence, 3),
                timestamp=None,
            ))

    return events


def _analyze_amplitude(audio_path: str | Path, window_sec: float = 0.5) -> list[AudioEvent]:
    """Basic amplitude spike detection on a WAV file.

    Detects sudden amplitude increases that may indicate impacts, and
    extended silence.
    """
    events: list[AudioEvent] = []

    try:
        with wave.open(str(audio_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            frame_rate = wf.getframerate()
            n_frames = wf.getnframes()

            if sample_width != 2:
                logger.debug("Skipping amplitude analysis: sample_width=%d", sample_width)
                return events

            window_frames = int(frame_rate * window_sec)
            if window_frames == 0:
                return events

            total_windows = n_frames // (window_frames * n_channels)
            if total_windows < 2:
                return events

            rms_values: list[tuple[float, float]] = []  # (timestamp, rms)

            for i in range(total_windows):
                raw = wf.readframes(window_frames)
                if not raw:
                    break
                samples = struct.unpack(f"<{len(raw) // 2}h", raw)
                # RMS
                mean_sq = sum(s * s for s in samples) / len(samples)
                rms = mean_sq ** 0.5
                timestamp = i * window_sec
                rms_values.append((timestamp, rms))

            if not rms_values:
                return events

            avg_rms = sum(r for _, r in rms_values) / len(rms_values)

            # Detect spikes (potential impacts)
            spike_threshold = avg_rms * 3.0
            for ts, rms in rms_values:
                if rms > spike_threshold and avg_rms > 100:
                    events.append(AudioEvent(
                        label="impact",
                        confidence=round(min(0.7, rms / (spike_threshold * 2)), 3),
                        timestamp=round(ts, 2),
                    ))

            # Detect silence
            silence_threshold = avg_rms * 0.1
            silent_windows = [(ts, rms) for ts, rms in rms_values if rms < silence_threshold]
            if len(silent_windows) > len(rms_values) * 0.3:
                events.append(AudioEvent(
                    label="silence",
                    confidence=round(len(silent_windows) / len(rms_values), 3),
                    timestamp=silent_windows[0][0] if silent_windows else None,
                ))

    except Exception:
        logger.exception("Amplitude analysis failed for %s", audio_path)

    return events


class HeuristicAudioAnalyzer(AudioAnalyzer):
    """Audio analyser combining transcript keyword matching and amplitude
    spike detection."""

    def analyze(
        self,
        audio_path: str | Path,
        transcript: str | None = None,
    ) -> list[AudioEvent]:
        events: list[AudioEvent] = []

        # Transcript keyword analysis
        if transcript:
            events.extend(_analyze_transcript_keywords(transcript))

        # Amplitude analysis on WAV
        audio_p = Path(audio_path)
        if audio_p.exists() and audio_p.suffix.lower() == ".wav":
            events.extend(_analyze_amplitude(audio_path))

        # Deduplicate by label (keep highest confidence)
        best: dict[str, AudioEvent] = {}
        for ev in events:
            existing = best.get(ev.label)
            if existing is None or ev.confidence > existing.confidence:
                best[ev.label] = ev

        result = sorted(best.values(), key=lambda e: e.confidence, reverse=True)
        logger.info("Audio analysis: %d events detected", len(result))
        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_audio_analyzer(analyzer_name: str = "heuristic") -> AudioAnalyzer:
    """Factory to obtain an audio analyzer by name."""
    if analyzer_name == "heuristic":
        return HeuristicAudioAnalyzer()
    raise ValueError(f"Unknown audio analyzer: {analyzer_name}")
