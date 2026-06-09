"""RAG retrieval of brand knowledge for content generation.

Strictly additive: if Pinecone/OpenAI aren't configured, the brand has no
ingested chunks, or anything errors, this returns "" and generation proceeds
exactly as before. Brand DNA is still injected directly into prompts elsewhere;
this surfaces the larger crawled knowledge corpus (and embedded DNA docs).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)


async def retrieve_brand_grounding(
    brand_id: str,
    query: str,
    db: Session,
    *,
    top_k: int = 6,
    max_chars: int = 4000,
) -> str:
    """Return a bounded block of the most relevant brand knowledge for `query`."""
    s = get_settings()
    if not s.openai_api_key or not s.pinecone_api_key:
        return ""

    # Cheap guard: skip the embedding+Pinecone round-trip if the brand has no
    # ingested knowledge chunks at all.
    from app.models import BrandKnowledgeChunk

    has_chunks = (
        db.query(BrandKnowledgeChunk.id)
        .filter(BrandKnowledgeChunk.brand_id == brand_id)
        .first()
        is not None
    )
    if not has_chunks:
        return ""

    try:
        from app.services.ingestion import get_pinecone_index, query_brand_knowledge

        index = get_pinecone_index(s)
        matches = await query_brand_knowledge(
            brand_id=brand_id,
            query=query,
            top_k=top_k,
            pinecone_index=index,
            openai_api_key=s.openai_api_key,
            embedding_model=s.embedding_model,
        )
    except Exception as exc:  # noqa: BLE001 - retrieval must never break generation
        logger.warning("Brand grounding retrieval failed for brand %s: %s", brand_id, exc)
        return ""

    parts: list[str] = []
    seen: set[str] = set()
    total = 0
    for m in matches:
        txt = (m.get("text") or "").strip()
        if not txt or txt in seen:
            continue
        seen.add(txt)
        if total + len(txt) > max_chars:
            txt = txt[: max(0, max_chars - total)]
        if not txt:
            break
        parts.append(txt)
        total += len(txt)
        if total >= max_chars:
            break
    return "\n---\n".join(parts).strip()
