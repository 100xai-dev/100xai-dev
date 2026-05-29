from __future__ import annotations

import json
import logging
from typing import Literal

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails."""


class LLMService:
    """
    Provider-agnostic LLM client via OpenRouter.
    Primary model: EXTRACTION_MODEL env var (default: anthropic/claude-3-5-sonnet).
    Fallback model: EXTRACTION_MODEL_FALLBACK (default: openai/gpt-4o).
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def call(
        self,
        model: str,
        prompt: str,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """Single-shot LLM call. Returns assistant's text content."""
        api_key = self._settings.openrouter_api_key
        if not api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured")

        payload: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._settings.app_url,
            "X-Title": "100xAI Brand DNA Extractor",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code >= 500:
                raise LLMError(f"LLM provider 5xx: {resp.status_code} — {resp.text[:200]}")
            if resp.status_code >= 400:
                raise LLMError(f"LLM provider 4xx: {resp.status_code} — {resp.text[:200]}")

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise LLMError("Empty content returned from LLM")
            return content

    async def call_with_fallback(
        self,
        prompt: str,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """
        Tries the primary extraction model; falls back once if it returns 5xx.
        """
        s = self._settings
        try:
            return await self.call(
                model=s.extraction_model,
                prompt=prompt,
                response_format=response_format,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except LLMError as e:
            if "5xx" in str(e):
                logger.warning("Primary LLM failed with 5xx — trying fallback: %s", e)
                return await self.call(
                    model=s.extraction_model_fallback,
                    prompt=prompt,
                    response_format=response_format,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            raise


def safe_json_parse(raw: str) -> dict:
    """Strip common LLM wrappers and parse JSON. Raises json.JSONDecodeError if unparseable."""
    s = raw.strip()
    # Strip markdown code fences
    if s.startswith("```"):
        lines = s.split("\n", 1)
        if len(lines) > 1:
            s = lines[1]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        if s.startswith("json\n"):
            s = s[5:]
    return json.loads(s)
