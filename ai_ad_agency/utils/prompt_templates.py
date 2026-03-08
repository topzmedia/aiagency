"""
Prompt templates for LLM calls.
All templates are parameterized and kept here for easy editing and auditability.
"""
from __future__ import annotations

from string import Template
from typing import Any, Dict, List


def render(template: str, **kwargs: Any) -> str:
    """Simple string format rendering."""
    return template.format(**kwargs)


# ---------------------------------------------------------------------------
# Hook Generation
# ---------------------------------------------------------------------------

HOOK_SYSTEM_PROMPT = """You are an expert direct-response copywriter for paid social media advertising.
You specialize in writing short, punchy hooks for video ads and static image headlines.
Your hooks must be attention-grabbing, scroll-stopping, and trigger curiosity, urgency, or emotion.
Never use clichés. Be specific. Write like a human, not a robot.
All hooks must be under {max_chars} characters and under {max_words} words."""

HOOK_USER_PROMPT = """Generate exactly {count} unique hooks for the following offer.

OFFER: {offer_name}
DESCRIPTION: {offer_description}
TARGET AUDIENCE: {target_audience}
PAIN POINTS: {pain_points}
BENEFITS: {benefits}
TONE: {tone}
CATEGORY: {category}

Category description:
{category_description}

Rules:
- Each hook must be under {max_chars} characters
- Each hook must be fresh, specific, and punchy
- Do NOT repeat the same concept
- Do NOT use generic phrases like "Are you tired of..." unless extremely specific
- Vary sentence structure
- Mix questions, statements, and partial sentences

Return ONLY a JSON array of strings. No explanation. No numbering. Just the array.
Example: ["Hook one here", "Hook two here", ...]"""

HOOK_CATEGORY_DESCRIPTIONS = {
    "curiosity": "Create intense curiosity — make the viewer desperate to know more. Use open loops, incomplete thoughts, or surprising claims.",
    "warning": "Alert the viewer to a danger, mistake, or risk they might be making. Create concern and urgency to avoid a bad outcome.",
    "discovery": "Reveal something new, surprising, or counterintuitive. Position it as a secret, loophole, or hidden truth.",
    "urgency": "Create urgency through time limits, scarcity, or consequences of inaction. Make them feel they must act now.",
    "authority": "Lead with credibility, expertise, or a contrarian insight. Sound like someone who knows something others don't.",
}


# ---------------------------------------------------------------------------
# Rotating Hook Variants
# ---------------------------------------------------------------------------

ROTATING_HOOK_SYSTEM = """You are a direct-response copywriter. Your job is to rephrase hooks
while preserving the core message and emotional trigger. Create fresh variations that feel different
but hit the same psychological note."""

ROTATING_HOOK_USER = """Take this original hook and create {count} distinct rephrased variants.

ORIGINAL HOOK: {hook_text}
OFFER CONTEXT: {offer_description}
HOOK CATEGORY: {category}

Rules:
- Each variant must feel distinct — different words, different structure
- Preserve the core emotional trigger and meaning
- Do NOT just rearrange words
- Vary between questions, statements, and declaratives
- Keep each under {max_chars} characters
- Reject any variant that is too similar to the original (similarity > 80%)

Return ONLY a JSON array of strings. No explanation."""


# ---------------------------------------------------------------------------
# Script Generation
# ---------------------------------------------------------------------------

SCRIPT_SYSTEM_PROMPT = """You are a world-class direct-response video script writer for paid social ads.
You write scripts that convert. You understand pacing, emotional arcs, and persuasion psychology.
You write for real humans to speak naturally on camera — no robotic language, no stiff sentences.
Scripts must feel authentic, conversational, and credible."""

SCRIPT_USER_PROMPT = """Write a {style} style video ad script based on this hook and offer.

HOOK: {hook_text}
OFFER: {offer_name}
OFFER DESCRIPTION: {offer_description}
TARGET AUDIENCE: {target_audience}
PAIN POINTS: {pain_points}
BENEFITS: {benefits}
CTA: {cta}
TONE: {tone}
VIDEO LENGTH: {length} ({length_description})
STYLE: {style} — {style_description}

The script MUST include these exact sections:
1. HOOK (the attention grabber — use or riff on the provided hook)
2. PROBLEM (agitate the pain point for the target audience)
3. DISCOVERY (introduce the solution/offer naturally)
4. BENEFIT (specific benefits and outcomes)
5. CTA (clear, direct call to action: "{cta}")

Length guidance: {length_description}

Return as JSON with this exact structure:
{{
  "hook": "...",
  "problem": "...",
  "discovery": "...",
  "benefit": "...",
  "cta": "...",
  "full_text": "...",
  "estimated_duration_sec": <integer>,
  "tags": ["tag1", "tag2"]
}}"""

SCRIPT_STYLE_DESCRIPTIONS = {
    "testimonial": "First-person story from a satisfied customer's perspective. Use 'I' and personal experiences.",
    "authority": "Expert or authority figure speaking with confidence and credentials. Lead with expertise.",
    "story": "Narrative arc with a beginning problem, turning point, and resolution. Hook with a story.",
    "direct_response": "Straight, punchy, benefit-focused. No fluff. Problem → Solution → CTA.",
    "comparison": "Compare before vs after, or this solution vs alternatives. Show contrast clearly.",
    "almost_missed": "First-person story of nearly missing out. Creates FOMO and relatability.",
    "news_update": "Journalistic style, breaking news tone. Position as important new information.",
}

SCRIPT_LENGTH_DESCRIPTIONS = {
    "short": "15-20 seconds when spoken. About 40-55 words. Very punchy. Only the essentials.",
    "medium": "30-45 seconds when spoken. About 80-120 words. Cover all sections but stay lean.",
    "long": "45-60 seconds when spoken. About 120-160 words. Full narrative arc.",
}


# ---------------------------------------------------------------------------
# Script Variant
# ---------------------------------------------------------------------------

SCRIPT_VARIANT_USER = """Create a variation of this script by changing {variation_aspect}.
Keep the core hook and offer the same but vary the {variation_aspect}.

ORIGINAL SCRIPT:
{original_full_text}

VARIATION INSTRUCTION: {variation_instruction}

Return the same JSON structure as the original with updated sections."""

VARIATION_ASPECTS = [
    {
        "aspect": "intro",
        "instruction": "Rewrite the hook and problem sections with a completely different opening approach. Keep discovery, benefit, and CTA the same.",
    },
    {
        "aspect": "cta",
        "instruction": "Rewrite the CTA section with different language and urgency. Make it softer/harder or more/less specific.",
    },
    {
        "aspect": "tone",
        "instruction": "Rewrite the entire script in a more conversational, casual tone. Make it sound like a text to a friend.",
    },
    {
        "aspect": "framing",
        "instruction": "Reframe the offer from a loss-aversion angle — what does the viewer LOSE by not acting?",
    },
    {
        "aspect": "benefit_emphasis",
        "instruction": "Expand the benefit section significantly. Add specific numbers, timeframes, and concrete outcomes.",
    },
]


# ---------------------------------------------------------------------------
# Image Generation
# ---------------------------------------------------------------------------

IMAGE_PROMPT_TEMPLATES: Dict[str, str] = {
    "lifestyle": (
        "Photorealistic lifestyle photo of {audience_description} in a {setting} setting. "
        "The person appears {emotional_state}. Natural lighting, candid feel, "
        "high quality DSLR photography. No text in image."
    ),
    "testimonial_still": (
        "Close-up portrait of a {age_group} {gender} looking directly at camera "
        "with a {expression} expression. Professional headshot style. Clean background. "
        "Natural, authentic, photorealistic. No text in image."
    ),
    "headline": (
        "Clean, modern graphic design background for an advertisement. "
        "{color_scheme} color palette. Minimal, professional. "
        "Space for headline text overlay. No actual text in image."
    ),
    "quote_card": (
        "Elegant card design with {color_scheme} background. "
        "Soft texture, professional look. Space for quote text overlay. "
        "No text in image."
    ),
    "infographic": (
        "Clean infographic-style background with {color_scheme} design elements. "
        "Modern, trustworthy, professional health/finance/lifestyle aesthetic. "
        "Space for data points and text. No actual text in image."
    ),
    "before_after": (
        "Split-panel visual comparing before and after states. "
        "Left side shows problem/pain state, right side shows solved/improved state. "
        "Photorealistic, no text in image."
    ),
    "ugc_screenshot": (
        "Authentic-looking screenshot style graphic resembling a social media post "
        "or text message conversation. Raw, unpolished, personal. "
        "Relatable UGC aesthetic. No identifying information."
    ),
}


# ---------------------------------------------------------------------------
# B-Roll / Video Prompts
# ---------------------------------------------------------------------------

BROLL_PROMPT_TEMPLATE = (
    "Cinematic video clip: {scene_description}. "
    "{mood} mood, {lighting} lighting, {camera_style} camera work. "
    "4K quality, professional production value. No people's faces visible unless specified."
)

BROLL_SCENE_TEMPLATES = {
    "kitchen_table": "Person's hands reviewing documents at a kitchen table, coffee cup nearby",
    "phone_scrolling": "Close-up of hands scrolling through a smartphone, warm home lighting",
    "paperwork": "Stack of documents and forms on a desk, professional setting",
    "relief_moment": "Person visibly relaxing, leaning back, relieved expression, natural light",
    "family_lifestyle": "Happy family moment at home, candid, warm natural lighting",
    "outdoor_walking": "Person walking confidently outdoors, urban or suburban setting",
    "computer_work": "Person working on laptop, focused, home office setting",
    "celebration": "Small personal celebration moment, hands raised, happy",
}


# ---------------------------------------------------------------------------
# Caption Generation
# ---------------------------------------------------------------------------

CAPTION_SYSTEM = """You are a subtitle editor. Convert script text into properly timed subtitle segments.
Each segment should be 2-8 words, easy to read in 2-3 seconds."""

CAPTION_USER = """Convert this script into subtitle segments for a {duration_sec}-second video.

SCRIPT:
{script_text}

Rules:
- Break into short readable chunks of 2-8 words each
- Timing must not exceed total video duration
- Keep each segment to 2-3 seconds max
- Ensure natural speech rhythm

Return as JSON array:
[{{"index": 0, "start_sec": 0.0, "end_sec": 2.5, "text": "First segment"}}, ...]"""
