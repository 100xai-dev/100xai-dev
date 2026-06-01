from __future__ import annotations

import json
import logging
from pathlib import Path

import jsonschema

from app.models import BrandKnowledgeSource
from app.services.llm import LLMError, LLMService, safe_json_parse
from app.services.prompts import render_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "brand_profile_v1.json"
_BRAND_PROFILE_SCHEMA: dict | None = None


def _load_schema() -> dict:
    global _BRAND_PROFILE_SCHEMA
    if _BRAND_PROFILE_SCHEMA is None:
        _BRAND_PROFILE_SCHEMA = json.loads(_SCHEMA_PATH.read_text())
    return _BRAND_PROFILE_SCHEMA


def validate_profile_schema(data: dict) -> list[str]:
    """Returns a list of validation error messages, empty if valid."""
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    return [f"{'.'.join(str(p) for p in e.absolute_path) or 'root'}: {e.message}" for e in errors]


class ExtractionValidationError(Exception):
    """Raised when LLM output fails schema validation after retry."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Schema validation failed: {errors}")


# ---------------------------------------------------------------------------
# Input assembly (spec §10.2)
# ---------------------------------------------------------------------------

def _token_count_approx(text: str) -> int:
    """Rough token count: words * 1.3."""
    return int(len(text.split()) * 1.3)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


def assemble_extraction_input(
    sources: list[BrandKnowledgeSource],
    manual_hints: dict,
    website_url: str | None,
) -> dict:
    """
    Assemble the LLM input blob from crawled sources and optional manual hints.
    Token budget cap: ~60,000 input tokens (approximated as chars/4).
    Returns a dict with keys: website_url, sections, visual_sources.
    """
    sections: list[dict] = []
    char_budget = 240_000  # ~60k tokens × 4 chars/token

    # 1. Manual hints first (highest signal)
    if manual_hints:
        hints_text = "\n".join(
            f"{k.replace('_', ' ').title()}: {v}"
            for k, v in manual_hints.items()
            if v
        )
        if hints_text:
            sections.append({"label": "TEAM NOTES FROM DISCOVERY CALL", "content": hints_text})

    # 2. Homepage
    homepage_source = None
    if website_url:
        from urllib.parse import urlparse
        base = urlparse(website_url).netloc.lower()
        for s in sources:
            if s.url and urlparse(s.url).netloc.lower() == base and urlparse(s.url).path.strip("/") == "":
                homepage_source = s
                break
    if not homepage_source and sources:
        homepage_source = sources[0]  # first source as fallback

    if homepage_source:
        sections.append({
            "label": f"HOMEPAGE — {homepage_source.url}",
            "content": _truncate(homepage_source.normalized_text or "", 32_000),
        })

    # 3. Priority pages (about, services, products, company)
    priority_keywords = ["about", "services", "products", "company", "solution", "feature"]
    priority_sources = [
        s for s in sources
        if s != homepage_source and s.url and any(k in s.url.lower() for k in priority_keywords)
    ]
    for s in priority_sources[:4]:
        sections.append({
            "label": f"PAGE — {s.metadata_json.get('title') or s.url}",
            "content": _truncate(s.normalized_text or "", 16_000),
        })

    # 4. Blog/insight pages
    blog_keywords = ["blog", "insight", "article", "resource"]
    blog_sources = [
        s for s in sources
        if s not in [homepage_source] + priority_sources[:4]
        and s.url and any(k in s.url.lower() for k in blog_keywords)
    ]
    used = sum(len(sec["content"]) for sec in sections)
    remaining = char_budget - used
    for s in blog_sources:
        budget_for_this = min(12_000, remaining // max(1, len(blog_sources)))
        if budget_for_this < 2_000:
            break
        sections.append({
            "label": f"BLOG — {s.metadata_json.get('title') or s.url}",
            "content": _truncate(s.normalized_text or "", budget_for_this),
        })
        remaining -= budget_for_this

    # 5. Remaining sources not yet covered
    covered = {homepage_source} | set(priority_sources[:4]) | set(blog_sources)
    for s in sources:
        if s in covered:
            continue
        remaining_now = char_budget - sum(len(sec["content"]) for sec in sections)
        if remaining_now < 2_000:
            break
        sections.append({
            "label": f"PAGE — {s.metadata_json.get('title') or s.url or 'additional'}",
            "content": _truncate(s.normalized_text or "", min(8_000, remaining_now)),
        })

    # Collect visual sources (screenshots and HTML) for visual DNA analysis
    visual_sources = []
    for s in sources:
        if s.screenshot_url or s.html_content:
            visual_sources.append({
                "url": s.url,
                "title": s.metadata_json.get("title") or s.url,
                "screenshot_url": s.screenshot_url,
                "html_content": s.html_content[:10000] if s.html_content else None,  # Limit HTML size
            })

    return {
        "website_url": website_url or "", 
        "sections": sections,
        "visual_sources": visual_sources
    }


# ---------------------------------------------------------------------------
# Extractor (spec §10.1)
# ---------------------------------------------------------------------------

async def extract_brand_profile(
    *,
    brand_id: str,
    sources: list[BrandKnowledgeSource],
    manual_hints: dict,
    website_url: str | None,
    extraction_model: str,
) -> dict:
    """
    Run LLM-based brand DNA extraction.
    Returns the parsed + validated profile dict.
    Raises ExtractionValidationError on persistent failure.
    """
    llm = LLMService()

    input_blob = assemble_extraction_input(sources, manual_hints, website_url)
    schema_json = json.dumps(_load_schema(), indent=2)
    
    # Check for visual sources and prepare for multimodal analysis
    visual_sources = input_blob.get("visual_sources", [])
    has_visual_content = bool(visual_sources)
    
    # Extract screenshot URLs for vision analysis
    screenshot_urls = []
    if has_visual_content:
        for vs in visual_sources:
            if vs.get("screenshot_url"):
                screenshot_urls.append(vs["screenshot_url"])
        # Limit to first 3 screenshots to avoid token limits
        screenshot_urls = screenshot_urls[:3]
    
    template_path = "brand_dna/v2/extraction_visual.txt" if has_visual_content else "brand_dna/v1/extraction.txt"
    
    prompt = render_prompt(
        template_path,
        {**input_blob, "schema_json": schema_json},
    )

    logger.info("Running extraction for brand %s (model=%s, sections=%d, screenshots=%d)",
                brand_id, extraction_model, len(input_blob["sections"]), len(screenshot_urls))

    try:
        raw_response = await llm.call_with_fallback(
            prompt=prompt,
            response_format="json",
            max_tokens=4000,
            temperature=0.3,
            images=screenshot_urls if screenshot_urls else None,
        )
    except LLMError as exc:
        raise ExtractionValidationError([f"LLM call failed: {exc}"]) from exc

    parsed = safe_json_parse(raw_response)
    validation_errors = validate_profile_schema(parsed)

    if validation_errors:
        logger.warning("Extraction schema validation failed (%d errors), retrying…",
                       len(validation_errors))
        # Use corresponding retry template
        retry_template = "brand_dna/v2/retry_visual.txt" if has_visual_content else "brand_dna/v1/retry.txt"
        retry_prompt = render_prompt(retry_template, {
            **input_blob,
            "schema_json": schema_json,
            "previous_response": raw_response,
            "validation_errors": validation_errors,
        })
        try:
            raw_response = await llm.call_with_fallback(
                prompt=retry_prompt,
                response_format="json",
                max_tokens=4000,
                temperature=0.2,
                images=screenshot_urls if screenshot_urls else None,
            )
        except LLMError as exc:
            raise ExtractionValidationError([f"LLM retry call failed: {exc}"]) from exc

        parsed = safe_json_parse(raw_response)
        validation_errors = validate_profile_schema(parsed)
        if validation_errors:
            raise ExtractionValidationError(validation_errors)

    logger.info("Extraction succeeded for brand %s", brand_id)
    return parsed
