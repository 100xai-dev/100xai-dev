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
# Pinecone index/client factory
# ---------------------------------------------------------------------------

# OpenAI embedding model output dimensions.
_EMBED_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def embedding_dimension(model: str) -> int:
    return _EMBED_DIMS.get(model, 1536)


def ensure_index(pc, name: str, *, dimension: int, metric: str = "cosine", cloud: str, region: str):
    """Return the Pinecone index, creating it (serverless) if it doesn't exist.

    NOTE: this only CREATES when missing. It does NOT fix an existing index that
    was created at the wrong dimension — that needs a manual delete+recreate.
    """
    from pinecone import ServerlessSpec

    existing = {i["name"] for i in pc.list_indexes()}
    if name not in existing:
        logger.info("Creating Pinecone index '%s' (dim=%d, %s/%s)", name, dimension, cloud, region)
        pc.create_index(
            name=name,
            dimension=dimension,
            metric=metric,
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        # Wait until the index reports ready.
        import time

        for _ in range(60):
            try:
                if pc.describe_index(name).get("status", {}).get("ready"):
                    break
            except Exception:  # noqa: BLE001 - transient while index spins up
                pass
            time.sleep(1)
    return pc.Index(name)


def get_pinecone_index(settings):
    """Single place that builds the Pinecone client + ensures the configured index.

    Reused by ingestion, re-ingestion/backfill, and RAG retrieval so the index
    name/dimension logic lives in exactly one spot.
    """
    from pinecone import Pinecone

    pc = Pinecone(api_key=settings.pinecone_api_key)
    return ensure_index(
        pc,
        settings.pinecone_index_name,
        dimension=embedding_dimension(settings.embedding_model),
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )


# ---------------------------------------------------------------------------
# Brand DNA → documents (so the structured profile is also retrievable)
# ---------------------------------------------------------------------------

def build_dna_chunks(brand_id: str, db, embedding_model: str) -> list[dict]:
    """Compose the BrandProfile (brand DNA) into a few small documents to embed.

    DNA is also injected directly into prompts at generation time; embedding it
    here just makes it retrievable alongside the knowledge corpus. DNA chunks are
    upserted to Pinecone only (not mirrored in Postgres — no source row exists).
    """
    from app.models import BrandProfile

    profile = db.query(BrandProfile).filter(BrandProfile.brand_id == brand_id).first()
    if not profile:
        return []

    def _join(v) -> str:
        if isinstance(v, (list, tuple)):
            return "; ".join(str(x) for x in v if x)
        return str(v or "")

    fields = {
        "positioning": "\n".join(filter(None, [
            f"Brand: {profile.name}" if profile.name else "",
            f"One-liner: {profile.one_liner}" if profile.one_liner else "",
            f"Industry: {profile.industry}" if profile.industry else "",
            f"Unique angle: {profile.unique_angle}" if profile.unique_angle else "",
        ])),
        "tone": _join(profile.tone_rules),
        "audience": _join(profile.audience_personas),
        "ctas": _join(profile.ctas),
        "proof_points": _join(profile.proof_points),
        "guardrails": "\n".join(filter(None, [
            f"Allowed topics: {_join(profile.allowed_topics)}",
            f"Disallowed topics: {_join(profile.disallowed_topics)}",
            f"Banned phrases: {_join(profile.banned_phrases)}",
            f"Messaging guardrails: {_join(profile.messaging_guardrails)}",
        ])),
    }

    chunks: list[dict] = []
    for field, text in fields.items():
        text = (text or "").strip()
        if len(text) < 10:
            continue
        chunks.append({
            "vector_id": f"{brand_id}:dna:{field}",
            "text": text,
            "metadata": {
                "brand_id": str(brand_id),
                "type": "dna",
                "field": field,
                "source_url": "",
            },
        })
    return chunks


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
) -> dict:
    """
    Idempotent ingestion: clears existing vectors for the brand, then re-ingests
    both the knowledge corpus (crawled sources) and the brand DNA documents.

    Returns a stats dict: {sources_total, sources_skipped_short, chunks_built,
    dna_docs, vectors_upserted}.
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

    # 2. Build knowledge chunks (mirrored in Postgres)
    sources_total = len(sources)
    sources_skipped_short = 0
    knowledge_chunks: list[dict] = []
    for source in sources:
        text = source.normalized_text
        if not text or len(text) < 50:
            sources_skipped_short += 1
            continue
        text_chunks = chunk_text(text)
        for idx, chunk in enumerate(text_chunks):
            knowledge_chunks.append({
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

    # 2b. Build DNA chunks (Pinecone-only — no Postgres source row to FK against)
    dna_chunks = build_dna_chunks(brand_id, db, embedding_model)

    all_chunks = knowledge_chunks + dna_chunks
    stats = {
        "sources_total": sources_total,
        "sources_skipped_short": sources_skipped_short,
        "chunks_built": len(knowledge_chunks),
        "dna_docs": len(dna_chunks),
        "vectors_upserted": 0,
    }
    if not all_chunks:
        logger.info("No chunks to ingest for brand %s (%s)", brand_id, stats)
        return stats

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

    # 4. Persist Postgres chunk mirror (knowledge chunks only)
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
        for c in knowledge_chunks
    ])
    db.flush()

    stats["vectors_upserted"] = total_upserted
    logger.info("Ingested %d vectors for brand %s (%s)", total_upserted, brand_id, stats)
    return stats


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
    # Pinecone SDK v3+ returns a QueryResponse object with `.matches`; older/dict
    # responses expose ["matches"]. Normalize to a list of plain dicts.
    matches = getattr(results, "matches", None)
    if matches is None:
        matches = results.get("matches", []) if hasattr(results, "get") else []
    normalized: list[dict] = []
    for m in matches:
        meta = (getattr(m, "metadata", None) or (m.get("metadata") if hasattr(m, "get") else {})) or {}
        score = getattr(m, "score", None)
        if score is None and hasattr(m, "get"):
            score = m.get("score")
        normalized.append({
            "text": meta.get("text", ""),
            "score": score,
            "source_url": meta.get("source_url", ""),
            "type": meta.get("type", "knowledge"),
        })
    return normalized


# ---------------------------------------------------------------------------
# Delete brand namespace
# ---------------------------------------------------------------------------

async def delete_brand_knowledge(brand_id: str, pinecone_index) -> None:
    """Idempotent. Safe to call even if namespace doesn't exist."""
    try:
        pinecone_index.delete(delete_all=True, namespace=str(brand_id))
    except Exception as exc:
        logger.warning("Pinecone delete namespace failed for brand %s: %s", brand_id, exc)
