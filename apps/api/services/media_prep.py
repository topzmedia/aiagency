"""Media preparation service.

Validates media files, probes metadata via ffprobe, extracts thumbnails and
audio tracks using ffmpeg subprocess calls.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported extensions
VALID_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
VALID_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a"}
VALID_EXTENSIONS = VALID_VIDEO_EXTENSIONS | VALID_AUDIO_EXTENSIONS


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MediaInfo:
    """Metadata extracted from a media file via ffprobe."""
    path: str
    duration_sec: float
    width: int | None
    height: int | None
    fps: float | None
    video_codec: str | None
    audio_codec: str | None
    file_size_bytes: int
    format_name: str


@dataclass
class ThumbnailResult:
    """Result of thumbnail extraction."""
    path: str
    timestamp_sec: float
    width: int
    height: int


@dataclass
class AudioExtractionResult:
    """Result of audio track extraction."""
    path: str
    duration_sec: float
    sample_rate: int
    channels: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_file(path: str | Path) -> bool:
    """Check that *path* exists and has a supported media extension.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    ValueError
        If the file extension is not in the supported set.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Media file not found: {path}")
    if p.suffix.lower() not in VALID_EXTENSIONS:
        raise ValueError(
            f"Unsupported media format '{p.suffix}'. "
            f"Supported: {sorted(VALID_EXTENSIONS)}"
        )
    return True


# ---------------------------------------------------------------------------
# ffprobe helper
# ---------------------------------------------------------------------------

def _run_ffprobe(path: str | Path) -> dict:
    """Run ffprobe and return parsed JSON output."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=True,
        )
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise RuntimeError("ffprobe not found – install FFmpeg to use media_prep")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed for {path}: {exc.stderr}") from exc
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timed out for {path}")


def probe_media(path: str | Path) -> MediaInfo:
    """Probe a media file and return structured :class:`MediaInfo`."""
    validate_file(path)
    data = _run_ffprobe(path)

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))
    format_name = fmt.get("format_name", "unknown")

    width = height = fps = None
    video_codec = audio_codec = None

    if video_stream:
        width = int(video_stream.get("width", 0)) or None
        height = int(video_stream.get("height", 0)) or None
        video_codec = video_stream.get("codec_name")
        # Parse frame rate
        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) else None
        except (ValueError, ZeroDivisionError):
            fps = None

    if audio_stream:
        audio_codec = audio_stream.get("codec_name")

    return MediaInfo(
        path=str(path),
        duration_sec=duration,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_codec,
        audio_codec=audio_codec,
        file_size_bytes=file_size,
        format_name=format_name,
    )


# ---------------------------------------------------------------------------
# Thumbnail extraction
# ---------------------------------------------------------------------------

def extract_thumbnail(
    path: str | Path,
    output_path: str | Path | None = None,
    timestamp: float = 1.0,
) -> ThumbnailResult:
    """Extract a single frame as a JPEG thumbnail.

    Parameters
    ----------
    path:
        Path to the source video.
    output_path:
        Where to write the thumbnail.  Defaults to ``<video_stem>_thumb.jpg``
        next to the source file.
    timestamp:
        The time (seconds) at which to capture the frame.
    """
    validate_file(path)
    p = Path(path)
    if output_path is None:
        output_path = p.parent / f"{p.stem}_thumb.jpg"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", str(path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=30, check=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found – install FFmpeg to use media_prep")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Thumbnail extraction failed: {exc.stderr}") from exc

    # Get thumbnail dimensions
    thumb_info = _run_ffprobe(out)
    vs = next(
        (s for s in thumb_info.get("streams", []) if s.get("codec_type") == "video"),
        {},
    )
    width = int(vs.get("width", 0))
    height = int(vs.get("height", 0))

    logger.info("Extracted thumbnail at %.1fs -> %s", timestamp, out)
    return ThumbnailResult(path=str(out), timestamp_sec=timestamp, width=width, height=height)


# ---------------------------------------------------------------------------
# Audio extraction
# ---------------------------------------------------------------------------

def extract_audio(
    path: str | Path,
    output_path: str | Path | None = None,
    sample_rate: int = 16000,
    mono: bool = True,
) -> AudioExtractionResult:
    """Extract the audio track from a video as a WAV file.

    Parameters
    ----------
    path:
        Path to the source video.
    output_path:
        Where to write the WAV file.  Defaults to ``<video_stem>.wav``.
    sample_rate:
        Target sample rate (default 16 kHz for ASR compatibility).
    mono:
        Downmix to mono if True.
    """
    validate_file(path)
    p = Path(path)
    if output_path is None:
        output_path = p.parent / f"{p.stem}.wav"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
    ]
    if mono:
        cmd.extend(["-ac", "1"])
    cmd.append(str(out))

    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found – install FFmpeg to use media_prep")
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Audio extraction failed: {exc.stderr}") from exc

    audio_probe = _run_ffprobe(out)
    audio_fmt = audio_probe.get("format", {})
    audio_stream = next(
        (s for s in audio_probe.get("streams", []) if s.get("codec_type") == "audio"),
        {},
    )

    duration = float(audio_fmt.get("duration", 0))
    sr = int(audio_stream.get("sample_rate", sample_rate))
    channels = int(audio_stream.get("channels", 1))

    logger.info("Extracted audio -> %s (%.1fs, %dHz, %dch)", out, duration, sr, channels)
    return AudioExtractionResult(path=str(out), duration_sec=duration, sample_rate=sr, channels=channels)
