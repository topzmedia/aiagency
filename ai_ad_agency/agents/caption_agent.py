"""
Caption Agent — generates SRT subtitle files and JSON caption data for scripts.
Supports LLM-driven caption timing and a simple fallback for offline use.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional, Union

from ..models.schemas import CaptionFile, CaptionLine, Script, ScriptVariant
from ..providers.llm_provider import BaseLLMProvider
from ..utils.config import AppConfig
from ..utils.io import ensure_dir, write_json, write_models_json
from ..utils.logging_utils import get_module_logger
from ..utils.prompt_templates import CAPTION_SYSTEM, CAPTION_USER

logger = get_module_logger("caption_agent")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORDS_PER_CHUNK = 6          # Target words per subtitle segment
_MAX_SEGMENT_SEC = 3.0        # Hard cap on segment duration


class CaptionAgent:
    """Generates timed subtitle files for video scripts."""

    def __init__(self, config: AppConfig, llm: BaseLLMProvider) -> None:
        self.config = config
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_captions(
        self,
        script: Union[Script, ScriptVariant],
        output_dir: str,
    ) -> Optional[CaptionFile]:
        """
        Generate captions for a single script.

        Attempts LLM-based timing first; falls back to simple chunked timing
        if the LLM call fails or returns invalid data.

        Returns a CaptionFile object or None if the output could not be written.
        """
        out_dir = Path(output_dir)
        ensure_dir(out_dir)

        script_id = _get_script_id(script)
        duration_sec = script.estimated_duration_sec

        # Determine output paths
        srt_path = str(out_dir / f"captions_{script_id}.srt")
        json_path = str(out_dir / f"captions_{script_id}.json")

        # Attempt LLM generation
        lines: Optional[List[CaptionLine]] = None
        try:
            lines = self._generate_via_llm(script)
        except Exception as exc:
            logger.warning(
                "CaptionAgent: LLM caption generation failed for script=%s: %s — using fallback",
                script_id,
                exc,
            )

        if not lines:
            logger.info(
                "CaptionAgent: using simple fallback captions for script=%s",
                script_id,
            )
            lines = self._simple_fallback_captions(script)

        if not lines:
            logger.error(
                "CaptionAgent: could not generate any captions for script=%s",
                script_id,
            )
            return None

        # Write outputs
        try:
            self._write_srt(lines, srt_path)
            write_json([line.model_dump(mode="json") for line in lines], json_path)
        except Exception as exc:
            logger.error(
                "CaptionAgent: failed to write caption files for script=%s: %s",
                script_id,
                exc,
            )
            return None

        caption_file = CaptionFile(
            script_id=script_id,
            srt_path=srt_path,
            json_path=json_path,
            lines=lines,
        )
        logger.info(
            "CaptionAgent: generated %d caption lines for script=%s",
            len(lines),
            script_id,
        )
        return caption_file

    def generate_batch(
        self,
        scripts: List[Union[Script, ScriptVariant]],
        output_dir: str,
    ) -> List[CaptionFile]:
        """Generate captions for a list of scripts. Skips failures."""
        if not scripts:
            return []

        results: List[CaptionFile] = []
        for idx, script in enumerate(scripts):
            script_id = _get_script_id(script)
            logger.info(
                "CaptionAgent: processing %d/%d — script=%s",
                idx + 1,
                len(scripts),
                script_id,
            )
            result = self.generate_captions(script, output_dir)
            if result is not None:
                results.append(result)

        logger.info(
            "CaptionAgent batch complete: %d/%d succeeded",
            len(results),
            len(scripts),
        )
        return results

    # ------------------------------------------------------------------
    # SRT writer
    # ------------------------------------------------------------------

    def _write_srt(self, lines: List[CaptionLine], path: str) -> None:
        """
        Write a properly formatted SRT subtitle file.

        Format:
            <index>
            HH:MM:SS,mmm --> HH:MM:SS,mmm
            Text here

            (blank line between entries)
        """
        srt_path = Path(path)
        srt_path.parent.mkdir(parents=True, exist_ok=True)

        with open(srt_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(lines):
                # SRT indices are 1-based
                f.write(f"{i + 1}\n")
                f.write(f"{_format_timestamp(line.start_sec)} --> {_format_timestamp(line.end_sec)}\n")
                f.write(f"{line.text.strip()}\n")
                f.write("\n")  # Blank line separator

        logger.debug("CaptionAgent: wrote SRT with %d entries → %s", len(lines), srt_path)

    # ------------------------------------------------------------------
    # LLM-based generation
    # ------------------------------------------------------------------

    def _generate_via_llm(self, script: Union[Script, ScriptVariant]) -> List[CaptionLine]:
        """
        Ask the LLM to segment the script into timed subtitle entries.
        Returns a list of CaptionLine objects.
        Raises ValueError / RuntimeError on bad response.
        """
        duration_sec = script.estimated_duration_sec
        system = CAPTION_SYSTEM
        user = CAPTION_USER.format(
            duration_sec=duration_sec,
            script_text=script.full_text,
        )

        raw = self.llm.complete_json(system, user, temperature=0.3, max_tokens=4096)

        if not isinstance(raw, list):
            raise ValueError(
                f"LLM returned unexpected type for captions: {type(raw)}"
            )

        lines: List[CaptionLine] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                line = CaptionLine(
                    index=int(item.get("index", len(lines))),
                    start_sec=float(item["start_sec"]),
                    end_sec=float(item["end_sec"]),
                    text=str(item.get("text", "")).strip(),
                )
                if line.text and line.end_sec > line.start_sec:
                    lines.append(line)
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug("CaptionAgent: skipping malformed caption entry: %s — %s", item, exc)
                continue

        if not lines:
            raise ValueError("LLM returned no valid caption lines")

        # Re-index sequentially
        for idx, line in enumerate(lines):
            line.index = idx

        return lines

    # ------------------------------------------------------------------
    # Simple fallback
    # ------------------------------------------------------------------

    def _simple_fallback_captions(
        self,
        script: Union[Script, ScriptVariant],
    ) -> List[CaptionLine]:
        """
        Split script.full_text into ~6-word chunks and assign equal timing
        across estimated_duration_sec.
        """
        text = script.full_text.strip()
        if not text:
            return []

        duration_sec = float(script.estimated_duration_sec)
        words = text.split()

        if not words:
            return []

        # Build chunks of ~_WORDS_PER_CHUNK words
        chunks: List[str] = []
        for i in range(0, len(words), _WORDS_PER_CHUNK):
            chunk = " ".join(words[i : i + _WORDS_PER_CHUNK])
            if chunk:
                chunks.append(chunk)

        if not chunks:
            return []

        # Distribute time evenly; cap each segment at _MAX_SEGMENT_SEC
        # If even distribution exceeds cap, we compress by inserting more
        # segments within the total duration.
        seg_duration = duration_sec / len(chunks)
        seg_duration = min(seg_duration, _MAX_SEGMENT_SEC)

        lines: List[CaptionLine] = []
        current_time = 0.0
        for idx, chunk in enumerate(chunks):
            start = current_time
            end = min(start + seg_duration, duration_sec)
            if end <= start:
                break
            lines.append(
                CaptionLine(
                    index=idx,
                    start_sec=round(start, 3),
                    end_sec=round(end, 3),
                    text=chunk,
                )
            )
            current_time = end

        return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_script_id(script: Union[Script, ScriptVariant]) -> str:
    """Return the appropriate ID field for Script or ScriptVariant."""
    if isinstance(script, Script):
        return script.script_id
    return script.variant_id


def _format_timestamp(seconds: float) -> str:
    """
    Convert a float seconds value to SRT timestamp format: HH:MM:SS,mmm
    """
    seconds = max(0.0, seconds)
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
