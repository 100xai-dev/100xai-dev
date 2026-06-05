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
    LLM client using Anthropic's official API.
    Primary model: EXTRACTION_MODEL env var (default: anthropic/claude-haiku-4-5-20251001).
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
        images: list[str] | None = None,
    ) -> str:
        """Single-shot LLM call to Anthropic API. Returns assistant's text content."""
        # Try Anthropic first, fallback to OpenRouter if needed
        if self._settings.anthropic_api_key and (model.startswith("claude") or model.startswith("anthropic/")):
            return await self._call_anthropic(model, prompt, response_format, max_tokens, temperature, images)
        elif self._settings.openrouter_api_key:
            return await self._call_openrouter(model, prompt, response_format, max_tokens, temperature, images)
        else:
            raise LLMError("Neither ANTHROPIC_API_KEY nor OPENROUTER_API_KEY is configured")

    async def _call_anthropic(
        self,
        model: str,
        prompt: str,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 4000,
        temperature: float = 0.3,
        images: list[str] | None = None,
    ) -> str:
        """Call Anthropic's official API."""
        api_key = self._settings.anthropic_api_key
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")
        
        # Remove 'anthropic/' prefix for official Anthropic API
        if model.startswith("anthropic/"):
            model = model.replace("anthropic/", "")

        # Build message content with optional images
        if images:
            content = [{"type": "text", "text": prompt}]
            for image_url in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_url  # Assume base64 encoded for Anthropic
                    }
                })
        else:
            content = prompt

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": content}]
        }

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            if resp.status_code >= 500:
                raise LLMError(f"Anthropic API 5xx: {resp.status_code} — {resp.text[:200]}")
            if resp.status_code >= 400:
                raise LLMError(f"Anthropic API 4xx: {resp.status_code} — {resp.text[:200]}")

            data = resp.json()
            if not data.get("content") or not data["content"]:
                raise LLMError("Empty content returned from Anthropic API")
            
            # Anthropic returns content as an array of blocks
            content_text = ""
            for block in data["content"]:
                if block.get("type") == "text":
                    content_text += block.get("text", "")
            
            if not content_text:
                raise LLMError("No text content found in Anthropic response")
            return content_text

    async def _call_openrouter(
        self,
        model: str,
        prompt: str,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 4000,
        temperature: float = 0.3,
        images: list[str] | None = None,
    ) -> str:
        """Fallback to OpenRouter API."""
        api_key = self._settings.openrouter_api_key
        if not api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured")

        # Build message content with optional images
        if images:
            content = [{"type": "text", "text": prompt}]
            for image_url in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
        else:
            content = prompt

        # Map Anthropic model names to OpenRouter format dynamically
        openrouter_model = model
        if model.startswith("claude"):
            # Convert any Anthropic model name to OpenRouter format
            # Handle specific known mappings, then fallback to generic format
            model_mappings = {
                "anthropic/claude-haiku-4-5-20251001": "anthropic/claude-haiku-4-5-20251001",
                "openai/gpt-4o": "openai/gpt-4o",
                "claude-3-5-sonnet": "anthropic/claude-3.5-sonnet",
                "claude-3-haiku": "anthropic/claude-3-haiku",
                "claude-3-opus": "anthropic/claude-3-opus",
                "claude-2": "anthropic/claude-2",
            }
            
            # Try exact match first
            if model in model_mappings:
                openrouter_model = model_mappings[model]
            else:
                # Generic fallback: try to map dynamically
                # Remove date suffixes and convert to OpenRouter format
                base_model = model.replace("-20241022", "").replace("-20240620", "")
                if base_model != model:
                    # Has a date suffix, try to map the base model
                    if base_model in model_mappings:
                        openrouter_model = model_mappings[base_model]
                    else:
                        openrouter_model = f"anthropic/{base_model}"
                else:
                    # No date suffix, use as-is
                    openrouter_model = f"anthropic/{model}"

        payload: dict = {
            "model": openrouter_model,
            "messages": [{"role": "user", "content": content}],
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
                raise LLMError(f"OpenRouter 5xx: {resp.status_code} — {resp.text[:200]}")
            if resp.status_code >= 400:
                raise LLMError(f"OpenRouter 4xx: {resp.status_code} — {resp.text[:200]}")

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise LLMError("Empty content returned from OpenRouter")
            return content

    async def call_with_fallback(
        self,
        prompt: str,
        response_format: Literal["text", "json"] = "text",
        max_tokens: int = 4000,
        temperature: float = 0.3,
        images: list[str] | None = None,
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
                images=images,
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
                    images=images,
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
