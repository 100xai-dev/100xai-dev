from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

logger = logging.getLogger(__name__)

# Prompts root is at backend/prompts/ relative to the repo.
# When running from backend/ directory (typical for uvicorn), this resolves correctly.
_PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"

_env = Environment(
    loader=FileSystemLoader(str(_PROMPTS_ROOT)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)


def render_prompt(template_path: str, context: dict) -> str:
    """
    Render a prompt template.

    template_path is relative to backend/prompts/, e.g. 'brand_dna/v1/extraction.txt'
    """
    template = _env.get_template(template_path)
    return template.render(**context)
