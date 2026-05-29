from __future__ import annotations

import logging
from typing import Iterator

import httpx
import tiktoken

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text chunking (spec §11.2)
# ---------------------------------------------------------------------------

_encoder: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")  # text-embedding-3-small uses this
    return _encoder


def count_tokens(text: str) -> int:
    return len(_get_encoder().encode(text))


def chunk_text(
    text: str,
    target_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[str]:
    """
    Split text into chunks of ~target_tokens with ~overlap_tokens overlap.
    Splits on paragraph boundaries first, then sentence boundaries.
    """
    encoder = _get_encoder()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush_chunk() -> None:
        if current:
            chunks.append("\n\n".join(current))

    for para in paragraphs:
        para_tokens = len(encoder.encode(para))

        if para_tokens > target_tokens:
            # Split by sentences (simple split on ". ")
            sentences = [s.strip() for s in para.replace("! ", ". ").replace("? ", ". ").split(". ") if s.strip()]
            for sent in sentences:
                sent_tokens = len(encoder.encode(sent))
                if current_tokens + sent_tokens > target_tokens and current:
                    flush_chunk()
                    # Overlap: keep last sentence(s)
                    if overlap_tokens > 0 and current:
                        current = [current[-1]]
                        current_tokens = len(encoder.encode(current[0]))
                    else:
                        current = []
                        current_tokens = 0
                current.append(sent)
                current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > target_tokens and current:
                flush_chunk()
                # Overlap: keep last paragraph
                if overlap_tokens > 0 and current:
                    current = [current[-1]]
                    current_tokens = len(encoder.encode(current[0]))
                else:
                    current = []
                    current_tokens = 0
            current.append(para)
            current_tokens += para_tokens

    flush_chunk()
    return [c for c in chunks if len(c) > 50]


# ---------------------------------------------------------------------------
# Embedding (spec §11.3)
# ---------------------------------------------------------------------------

async def embed_batch(texts: list[str], api_key: str, model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generate embeddings for a batch of texts using OpenAI API."""
    if not texts:
        return []
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]


def _batched(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


# ---------------------------------------------------------------------------
# Pinecone ingestion (spec §11.4)
# ---------------------------------------------------------------------------

async def ingest_brand_knowledge(
    *,
    brand_id: str,
    sources: list,  # list of BrandKnowledgeSource ORM objects
    db,  # SQLAlchemy session
    pinecone_index,  # pinecone Index object
    openai_api_key: str,
    embedding_model: str = "text-embedding-3-small",
) -> int:
    """
    Idempotent ingestion: clears existing vectors for the brand, then re-ingests.
    Returns total number of vectors upserted.
    """
    from app.models import BrandKnowledgeChunk

    namespace = str(brand_id)

    # 1. Clear existing Pinecone namespace + Postgres chunks
    try:
        pinecone_index.delete(delete_all=True, namespace=namespace)
    except Exception as exc:
        logger.warning("Pinecone delete namespace failed (may not exist): %s", exc)

    db.query(BrandKnowledgeChunk).filter(BrandKnowledgeChunk.brand_id == brand_id).delete()
    db.flush()

    # 2. Build all chunks
    all_chunks: list[dict] = []
    for source in sources:
        text = source.normalized_text
        if not text or len(text) < 50:
            continue
        text_chunks = chunk_text(text)
        for idx, chunk in enumerate(text_chunks):
            all_chunks.append({
                "brand_id": brand_id,
                "source_id": source.id,
                "chunk_index": idx,
                "text": chunk,
                "token_count": count_tokens(chunk),
                "vector_id": f"{brand_id}:{source.id}:{idx}",
                "metadata": {
                    "brand_id": str(brand_id),
                    "source_id": str(source.id),
                    "source_type": source.source_type,
                    "source_url": source.url or "",
                    "chunk_index": idx,
                },
            })

    if not all_chunks:
        logger.info("No chunks to ingest for brand %s", brand_id)
        return 0

    # 3. Embed + upsert in batches of 100
    total_upserted = 0
    for batch in _batched(all_chunks, 100):
        embeddings = await embed_batch(
            [c["text"] for c in batch],
            api_key=openai_api_key,
            model=embedding_model,
        )
        vectors = [
            {
                "id": c["vector_id"],
                "values": emb,
                "metadata": {**c["metadata"], "text": c["text"][:1000]},
            }
            for c, emb in zip(batch, embeddings)
        ]
        pinecone_index.upsert(vectors=vectors, namespace=namespace)
        total_upserted += len(vectors)

    # 4. Persist Postgres chunk mirror
    from app.models import BrandKnowledgeChunk

    db.bulk_save_objects([
        BrandKnowledgeChunk(
            brand_id=c["brand_id"],
            source_id=c["source_id"],
            chunk_index=c["chunk_index"],
            text=c["text"],
            token_count=c["token_count"],
            vector_id=c["vector_id"],
            embedding_model=embedding_model,
            namespace=namespace,
        )
        for c in all_chunks
    ])
    db.flush()

    logger.info("Ingested %d vectors for brand %s", total_upserted, brand_id)
    return total_upserted


# ---------------------------------------------------------------------------
# Query (for downstream pipeline use)
# ---------------------------------------------------------------------------

async def query_brand_knowledge(
    *,
    brand_id: str,
    query: str,
    top_k: int = 5,
    pinecone_index,
    openai_api_key: str,
    embedding_model: str = "text-embedding-3-small",
) -> list[dict]:
    """Retrieve top_k brand knowledge chunks relevant to query."""
    embeddings = await embed_batch([query], api_key=openai_api_key, model=embedding_model)
    query_vector = embeddings[0]
    results = pinecone_index.query(
        vector=query_vector,
        top_k=top_k,
        namespace=str(brand_id),
        include_metadata=True,
    )
    return results.get("matches", [])


# ---------------------------------------------------------------------------
# Delete brand namespace
# ---------------------------------------------------------------------------

async def delete_brand_knowledge(brand_id: str, pinecone_index) -> None:
    """Idempotent. Safe to call even if namespace doesn't exist."""
    try:
        pinecone_index.delete(delete_all=True, namespace=str(brand_id))
    except Exception as exc:
        logger.warning("Pinecone delete namespace failed for brand %s: %s", brand_id, exc)
