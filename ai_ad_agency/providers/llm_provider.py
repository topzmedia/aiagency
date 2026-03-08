"""
LLM provider adapter.
Abstracts OpenAI (and compatible endpoints) for text generation.
Swap providers by changing config — the agent code stays the same.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.enums import LLMProvider
from ..utils.config import LLMProviderConfig
from ..utils.logging_utils import log_provider_call, log_provider_response
from ..utils.rate_limits import get_limiter
from ..utils.retries import ProviderRateLimitError, ProviderTimeoutError, TransientError

logger = logging.getLogger("ai_ad_agency.providers.llm")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Abstract interface that all LLM providers must implement."""

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        """Run a chat completion and return the response text."""

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> Any:
        """
        Run a completion expecting a JSON response.
        Parses and returns the Python object.
        Raises ValueError if parsing fails.
        """
        raw = self.complete(system_prompt, user_prompt, temperature, max_tokens)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to extract JSON from within the text
            import re
            match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            logger.error("JSON parse failed. Raw response:\n%s", cleaned[:500])
            raise ValueError(f"LLM returned invalid JSON: {e}") from e


# ---------------------------------------------------------------------------
# OpenAI / compatible provider
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI ChatCompletion provider.
    Also works with any OpenAI-compatible endpoint (Together, Groq, LM Studio, etc.)
    via base_url override.
    """

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._limiter = get_limiter("llm", config.requests_per_minute)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )
            kwargs: Dict[str, Any] = {"api_key": self.config.api_key}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        self._limiter.acquire()
        client = self._get_client()

        log_provider_call(
            logger,
            "openai",
            "chat.completions.create",
            f"model={self.config.model} temp={temperature} tokens={max_tokens} prompt_len={len(user_prompt)}",
        )

        try:
            response = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content or ""
            log_provider_response(
                logger, "openai", "chat.completions.create", "200",
                f"tokens_used={response.usage.total_tokens if response.usage else 'N/A'}"
            )
            return text

        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str:
                raise ProviderRateLimitError(f"OpenAI rate limit: {e}") from e
            if "timeout" in err_str:
                raise ProviderTimeoutError(f"OpenAI timeout: {e}") from e
            if "502" in err_str or "503" in err_str or "connection" in err_str:
                raise TransientError(f"OpenAI transient error: {e}") from e
            logger.error("OpenAI fatal error: %s", e)
            raise


# ---------------------------------------------------------------------------
# Mock provider (for testing / offline mode)
# ---------------------------------------------------------------------------

class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider that returns deterministic canned responses.
    Used in tests and when no API key is available.
    """

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> str:
        logger.debug("[MOCK LLM] complete() called")
        # Detect what kind of response is expected and return appropriate mock
        up = user_prompt.lower()

        if "generate" in up and "hook" in up:
            # Return mock hook array
            hooks = [
                f"Mock hook {i+1}: Are you making this costly mistake?" for i in range(10)
            ]
            return json.dumps(hooks)

        if "variant" in up and "hook" in up:
            variants = [f"Mock variant {i+1}: Don't ignore this warning" for i in range(5)]
            return json.dumps(variants)

        if "script" in up or "write a" in up:
            return json.dumps({
                "hook": "This one thing changed everything for me.",
                "problem": "Most people struggle with unexpected costs and have no idea why.",
                "discovery": "I discovered a simple solution that took less than 5 minutes.",
                "benefit": "Now I feel confident and protected, and it costs almost nothing.",
                "cta": "Click the link below to learn more today.",
                "full_text": (
                    "This one thing changed everything for me. "
                    "Most people struggle with unexpected costs and have no idea why. "
                    "I discovered a simple solution that took less than 5 minutes. "
                    "Now I feel confident and protected, and it costs almost nothing. "
                    "Click the link below to learn more today."
                ),
                "estimated_duration_sec": 20,
                "tags": ["mock", "direct_response"],
            })

        if "subtitle" in up or "caption" in up:
            return json.dumps([
                {"index": 0, "start_sec": 0.0, "end_sec": 2.5, "text": "Mock caption line one"},
                {"index": 1, "start_sec": 2.5, "end_sec": 5.0, "text": "Mock caption line two"},
                {"index": 2, "start_sec": 5.0, "end_sec": 8.0, "text": "Learn more today."},
            ])

        return json.dumps({"mock": True, "text": "Mock LLM response"})

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.9,
        max_tokens: int = 2048,
    ) -> Any:
        raw = self.complete(system_prompt, user_prompt, temperature, max_tokens)
        return json.loads(raw)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_llm_provider(config: LLMProviderConfig) -> BaseLLMProvider:
    """Factory that returns the correct provider based on config."""
    if config.provider == LLMProvider.OPENAI:
        if not config.api_key:
            logger.warning("No OpenAI API key set — using MockLLMProvider")
            return MockLLMProvider()
        return OpenAIProvider(config)
    elif config.provider in (LLMProvider.ANTHROPIC, LLMProvider.TOGETHER, LLMProvider.GROQ):
        # These all expose OpenAI-compatible endpoints
        if not config.api_key:
            logger.warning("No API key for %s — using MockLLMProvider", config.provider)
            return MockLLMProvider()
        # Map provider → base_url if not overridden
        if not config.base_url:
            base_urls = {
                LLMProvider.ANTHROPIC: None,  # Not OpenAI-compatible without wrapper
                LLMProvider.TOGETHER: "https://api.together.xyz/v1",
                LLMProvider.GROQ: "https://api.groq.com/openai/v1",
            }
            cfg = config.model_copy(update={"base_url": base_urls.get(config.provider)})
        else:
            cfg = config
        if config.provider == LLMProvider.ANTHROPIC:
            logger.warning(
                "Anthropic not natively OpenAI-compatible. Using OpenAIProvider with custom base_url. "
                "Set base_url to an Anthropic-compatible proxy or switch provider to openai."
            )
        return OpenAIProvider(cfg)
    else:
        logger.warning("Unknown LLM provider %s — using MockLLMProvider", config.provider)
        return MockLLMProvider()
