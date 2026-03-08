"""
CTA Agent — generates and manages call-to-action text variations.
Provides LLM-driven CTA generation as well as hardcoded offline fallbacks.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from ..models.enums import ScriptStyle
from ..models.schemas import OfferConfig
from ..providers.llm_provider import BaseLLMProvider
from ..utils.config import AppConfig
from ..utils.dedupe import TextDedupe
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("cta_agent")

# ---------------------------------------------------------------------------
# CTA character limit
# ---------------------------------------------------------------------------

_MAX_CTA_CHARS = 60


class CTAAgent:
    """Generates and manages CTA text variations for ad creatives."""

    # ------------------------------------------------------------------
    # Built-in CTAs for offline / fallback use
    # ------------------------------------------------------------------

    BUILT_IN_CTAS: Dict[str, List[str]] = {
        ScriptStyle.TESTIMONIAL: [
            "I got mine at the link below — check it out",
            "See where I found mine — tap the link",
            "It worked for me, maybe it will for you too",
            "Click below — it only took me 5 minutes",
            "I wish I'd found this sooner — link below",
        ],
        ScriptStyle.AUTHORITY: [
            "Find out if you qualify — click to check now",
            "Verify your eligibility in under 2 minutes",
            "See the official requirements — link below",
            "Check your status before this changes",
            "Review the full details at the link below",
        ],
        ScriptStyle.DIRECT_RESPONSE: [
            "Click now to claim your benefit",
            "Don't wait — tap the link below",
            "Act now — limited availability",
            "Get yours today — click below",
            "Claim it before it's gone — link below",
        ],
        ScriptStyle.STORY: [
            "Find out if your story ends differently — click",
            "Your situation may qualify — check now",
            "See how this could change things for you",
            "Start your own story — click the link below",
            "One click could be all it takes — try now",
        ],
        ScriptStyle.COMPARISON: [
            "Compare your options — see which is right for you",
            "Don't settle — see what you actually qualify for",
            "Stop overpaying — click to find a better option",
            "See the difference for yourself — click below",
            "Check what others are paying — link below",
        ],
        ScriptStyle.ALMOST_MISSED: [
            "Don't miss this — check now before it expires",
            "Almost missed mine — don't let that happen to you",
            "Click fast — this won't last much longer",
            "I almost skipped this — glad I didn't. You?",
            "One minute could change everything — click below",
        ],
        ScriptStyle.NEWS_UPDATE: [
            "Read the full update — link below",
            "See if this applies to you — click now",
            "Stay informed — check the details today",
            "This just changed — find out how it affects you",
            "Breaking: click below to get the full story",
        ],
    }

    def __init__(self, config: AppConfig, llm: BaseLLMProvider) -> None:
        self.config = config
        self.llm = llm

    # ------------------------------------------------------------------
    # LLM-driven generation
    # ------------------------------------------------------------------

    def generate_cta_variations(
        self,
        base_cta: str,
        offer: OfferConfig,
        count: int = 10,
    ) -> List[str]:
        """
        Generate `count` CTA text variations using the LLM.

        Each variation must be under 60 characters.
        Includes urgency, curiosity, and direct variants.
        Falls back to shuffled built-in CTAs on LLM failure.
        Returns a deduplicated list of CTA strings.
        """
        system_prompt = (
            "Generate direct-response CTA text variations for paid social media ads. "
            "Each CTA must be under 60 characters. "
            "Include urgency-based, curiosity-based, and direct-response variants. "
            "Return ONLY a JSON array of strings. No explanation."
        )
        user_prompt = (
            f"Generate exactly {count} unique CTA variations based on this base CTA:\n\n"
            f"BASE CTA: {base_cta}\n\n"
            f"OFFER: {offer.offer_name}\n"
            f"TARGET AUDIENCE: {offer.target_audience}\n"
            f"TONE: {', '.join(offer.tone) if offer.tone else 'professional, direct'}\n\n"
            f"Requirements:\n"
            f"- Each CTA must be under {_MAX_CTA_CHARS} characters\n"
            f"- Mix urgency, curiosity, and direct-response styles\n"
            f"- Avoid repeating the same phrase pattern\n"
            f"- Sound human and conversational\n\n"
            f"Return ONLY a JSON array of strings."
        )

        raw_ctas: List[str] = []
        try:
            result = self.llm.complete_json(system_prompt, user_prompt, temperature=0.85, max_tokens=1024)
            if isinstance(result, list):
                raw_ctas = [str(item).strip() for item in result if item and str(item).strip()]
            elif isinstance(result, dict):
                for key in ("ctas", "variations", "results", "data"):
                    if isinstance(result.get(key), list):
                        raw_ctas = [str(item).strip() for item in result[key] if item]
                        break
        except Exception as exc:
            logger.warning("CTAAgent: LLM generation failed: %s — falling back to built-ins", exc)

        if not raw_ctas:
            logger.info("CTAAgent: no LLM CTAs produced, using built-in fallbacks")
            raw_ctas = self._collect_builtin_ctas()

        # Filter length and deduplicate
        dedupe = TextDedupe(similarity_threshold=0.80)
        filtered: List[str] = []
        for cta in raw_ctas:
            cta = cta.strip()
            if not cta:
                continue
            if len(cta) > _MAX_CTA_CHARS:
                # Try trimming at last word boundary
                cta = cta[:_MAX_CTA_CHARS].rsplit(" ", 1)[0].rstrip(".,;:")
            if not cta:
                continue
            if dedupe.add(cta):
                filtered.append(cta)

        logger.info(
            "CTAAgent: generated %d CTA variations (requested %d)",
            len(filtered),
            count,
        )
        return filtered[:count] if len(filtered) > count else filtered

    # ------------------------------------------------------------------
    # Style-aware selection
    # ------------------------------------------------------------------

    def get_cta_for_style(self, style: ScriptStyle, base_cta: str) -> str:
        """
        Return a style-appropriate CTA variant.

        Maps ScriptStyle to specific CTA language patterns:
          - testimonial:      first-person "I got mine at..."
          - authority:        "Find out if you qualify..."
          - direct_response:  "Click now to..."
          - urgency (story/almost_missed): "Don't wait..."
          - others:           return base_cta
        """
        style_val = style.value if hasattr(style, "value") else str(style)

        style_cta_map: Dict[str, str] = {
            ScriptStyle.TESTIMONIAL:    "I got mine at the link below — check it out",
            ScriptStyle.AUTHORITY:      "Find out if you qualify — click to check now",
            ScriptStyle.DIRECT_RESPONSE: "Click now to claim your benefit",
            ScriptStyle.STORY:          "Don't wait — see if this applies to you",
            ScriptStyle.ALMOST_MISSED:  "Don't wait — check now before it expires",
            ScriptStyle.COMPARISON:     "Compare your options — click below",
            ScriptStyle.NEWS_UPDATE:    "See if this applies to you — click now",
        }

        # Prefer the mapped CTA; fall back to base_cta if not mapped or too long
        mapped = style_cta_map.get(style, base_cta)
        if len(mapped) <= _MAX_CTA_CHARS:
            return mapped

        # If mapped is too long, try base_cta, then a trimmed version
        if base_cta and len(base_cta) <= _MAX_CTA_CHARS:
            return base_cta

        return base_cta[:_MAX_CTA_CHARS].rsplit(" ", 1)[0]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_builtin_ctas(self) -> List[str]:
        """Flatten all built-in CTAs into a single shuffled list."""
        all_ctas: List[str] = []
        for style_ctas in self.BUILT_IN_CTAS.values():
            all_ctas.extend(style_ctas)
        random.shuffle(all_ctas)
        return all_ctas
