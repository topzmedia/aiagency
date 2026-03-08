"""
FFmpeg wrapper utilities for video assembly, conversion, and inspection.
All FFmpeg calls go through here for consistency and testability.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ai_ad_agency.ffmpeg")


# ---------------------------------------------------------------------------
# FFmpeg availability check
# ---------------------------------------------------------------------------

def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available in PATH."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_ffprobe() -> bool:
    """Return True if ffprobe is available in PATH."""
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_ffmpeg(
    cmd: List[str],
    label: str = "ffmpeg",
    timeout: int = 600,
    log_stderr: bool = True,
) -> Tuple[bool, str]:
    """
    Execute an FFmpeg command. Returns (success, stderr_output).

    Args:
        cmd: Full command list starting with 'ffmpeg'.
        label: Human-readable label for logging.
        timeout: Timeout in seconds.
        log_stderr: Whether to log stderr on failure.
    """
    logger.debug("[FFMPEG] %s: %s", label, " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            if log_stderr:
                logger.error(
                    "[FFMPEG FAILED] %s\nCMD: %s\nSTDERR: %s",
                    label,
                    " ".join(cmd),
                    result.stderr[-2000:],
                )
            return False, result.stderr
        logger.debug("[FFMPEG OK] %s", label)
        return True, result.stderr
    except subprocess.TimeoutExpired:
        msg = f"FFmpeg timed out after {timeout}s for: {label}"
        logger.error(msg)
        return False, msg
    except FileNotFoundError:
        msg = "ffmpeg not found in PATH. Please install FFmpeg."
        logger.error(msg)
        return False, msg


# ---------------------------------------------------------------------------
# Concat / Assembly
# ---------------------------------------------------------------------------

def concatenate_videos(
    input_paths: List[str | Path],
    output_path: str | Path,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    crf: int = 23,
    preset: str = "medium",
    audio_bitrate: str = "128k",
    threads: int = 4,
) -> bool:
    """
    Concatenate multiple video files using the FFmpeg concat demuxer.
    All inputs must have the same resolution and codec characteristics.
    Returns True on success.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write concat list file
    concat_file = output_path.with_suffix(".concat.txt")
    with open(concat_file, "w") as f:
        for p in input_paths:
            f.write(f"file '{Path(p).resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c:v", video_codec,
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-threads", str(threads),
        "-movflags", "+faststart",
        str(output_path),
    ]
    ok, _ = run_ffmpeg(cmd, label=f"concat→{output_path.name}")
    concat_file.unlink(missing_ok=True)
    return ok


def add_subtitles(
    video_path: str | Path,
    srt_path: str | Path,
    output_path: str | Path,
    font_size: int = 28,
    font_color: str = "white",
    border_style: int = 1,
) -> bool:
    """
    Burn subtitles from an SRT file into a video using FFmpeg subtitles filter.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subtitle_filter = (
        f"subtitles='{Path(srt_path).resolve()}':"
        f"force_style='FontSize={font_size},"
        f"PrimaryColour=&H00{font_color.lstrip('#')}&,"
        f"BorderStyle={border_style}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", subtitle_filter,
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"subtitles→{output_path.name}")[0]


def add_text_overlay(
    video_path: str | Path,
    text: str,
    output_path: str | Path,
    x: str = "(w-text_w)/2",
    y: str = "50",
    font_size: int = 52,
    font_color: str = "white",
    box_color: str = "black@0.5",
    start_sec: float = 0.0,
    end_sec: float = 3.0,
    font_file: Optional[str] = None,
) -> bool:
    """
    Overlay text on a video for a time range using drawtext filter.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escape special FFmpeg drawtext chars
    safe_text = text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

    font_part = f":fontfile='{font_file}'" if font_file and Path(font_file).exists() else ""
    enable_expr = f"between(t,{start_sec},{end_sec})"

    drawtext = (
        f"drawtext=text='{safe_text}'"
        f":fontsize={font_size}"
        f":fontcolor={font_color}"
        f":box=1:boxcolor={box_color}:boxborderw=10"
        f":x={x}:y={y}"
        f":enable='{enable_expr}'"
        f"{font_part}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", drawtext,
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"text_overlay→{output_path.name}")[0]


def create_text_card(
    text: str,
    output_path: str | Path,
    width: int = 1080,
    height: int = 1920,
    duration_sec: float = 2.5,
    bg_color: str = "#000000",
    font_color: str = "white",
    font_size: int = 60,
    font_file: Optional[str] = None,
) -> bool:
    """
    Create a solid-color video card with centered text overlay.
    Useful for hook cards and CTA end cards.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    safe_text = text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
    font_part = f":fontfile='{font_file}'" if font_file and Path(font_file).exists() else ""

    drawtext = (
        f"drawtext=text='{safe_text}'"
        f":fontsize={font_size}"
        f":fontcolor={font_color}"
        f":x=(w-text_w)/2:y=(h-text_h)/2"
        f":line_spacing=10"
        f"{font_part}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:size={width}x{height}:rate=30:duration={duration_sec}",
        "-vf", drawtext,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"text_card→{output_path.name}")[0]


def create_silent_audio(duration_sec: float, output_path: str | Path) -> bool:
    """Generate a silent audio file of the given duration."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duration_sec),
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"silent_audio→{output_path.name}")[0]


def add_audio_to_video(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    video_codec: str = "copy",
    audio_codec: str = "aac",
) -> bool:
    """Replace/add audio track to video."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", video_codec,
        "-c:a", audio_codec,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"add_audio→{output_path.name}")[0]


def scale_video(
    input_path: str | Path,
    output_path: str | Path,
    width: int,
    height: int,
    pad: bool = True,
) -> bool:
    """Scale a video to target dimensions, optionally padding."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if pad:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        )
    else:
        vf = f"scale={width}:{height}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"scale→{output_path.name}")[0]


def extract_audio(
    video_path: str | Path,
    output_path: str | Path,
    codec: str = "libmp3lame",
    bitrate: str = "192k",
) -> bool:
    """Extract audio from video file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-c:a", codec,
        "-b:a", bitrate,
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"extract_audio→{output_path.name}")[0]


def trim_video(
    input_path: str | Path,
    output_path: str | Path,
    start_sec: float = 0.0,
    duration_sec: Optional[float] = None,
    end_sec: Optional[float] = None,
) -> bool:
    """Trim a video clip."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-i", str(input_path), "-ss", str(start_sec)]
    if duration_sec is not None:
        cmd += ["-t", str(duration_sec)]
    elif end_sec is not None:
        cmd += ["-to", str(end_sec)]
    cmd += ["-c", "copy", str(output_path)]
    return run_ffmpeg(cmd, label=f"trim→{output_path.name}")[0]


def get_duration(path: str | Path) -> Optional[float]:
    """Get video/audio duration in seconds using ffprobe."""
    from .validators import probe_media
    info = probe_media(str(path))
    if info:
        return info.get("duration")
    return None


def get_dimensions(path: str | Path) -> Optional[Tuple[int, int]]:
    """Return (width, height) of a video file."""
    from .validators import probe_media
    info = probe_media(str(path))
    if info:
        w = info.get("width", 0)
        h = info.get("height", 0)
        if w and h:
            return w, h
    return None


def image_to_video(
    image_path: str | Path,
    output_path: str | Path,
    duration_sec: float = 5.0,
    width: int = 1080,
    height: int = 1920,
    zoom_pan: bool = True,
) -> bool:
    """
    Convert a static image to a video clip with optional Ken Burns zoom/pan.
    Used as B-roll fallback when live video generation is unavailable.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fps = 30
    total_frames = int(duration_sec * fps)

    if zoom_pan:
        # Ken Burns effect: subtle zoom from 1.0x to 1.05x
        zoompan = (
            f"zoompan=z='min(zoom+0.0005,1.05)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:fps={fps}:s={width}x{height}"
        )
        vf = f"scale={width*2}:{height*2},{zoompan},scale={width}:{height}"
    else:
        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-movflags", "+faststart",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"img2video→{output_path.name}")[0]


def mix_audio(
    video_path: str | Path,
    music_path: str | Path,
    output_path: str | Path,
    music_volume: float = 0.08,
) -> bool:
    """Mix background music at low volume with existing video audio."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(music_path),
        "-filter_complex",
        f"[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]
    return run_ffmpeg(cmd, label=f"mix_audio→{output_path.name}")[0]
