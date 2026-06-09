from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.deps import get_current_user, get_db, CurrentUser
from app.models import Brand, BrandKnowledgeSource, AuditLog, Job
from app.models.base import uuid_str
from app.services.job_dispatcher import JobDispatcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brands/{brand_id}/sources", tags=["brand-sources"])


class AddSourceIn(BaseModel):
    source_type: str  # 'manual_text' | 'uploaded_doc'
    title: Optional[str] = None
    storage_key: Optional[str] = None   # for uploaded_doc
    raw_text: Optional[str] = None      # for manual_text
    metadata: dict = {}


def _get_brand_scoped(brand_id: str, db: Session, org_id: str) -> Brand:
    brand = db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == org_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _source_to_dict(s: BrandKnowledgeSource) -> dict:
    return {
        "id": s.id,
        "brand_id": s.brand_id,
        "source_type": s.source_type,
        "title": s.title,
        "url": s.url,
        "storage_key": s.storage_key,
        "word_count": s.word_count,
        "fetched_at": s.fetched_at.isoformat() if s.fetched_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "metadata": s.metadata_json,
    }


# ---------------------------------------------------------------------------
# GET /v1/brands/:id/sources
# ---------------------------------------------------------------------------

@router.get("")
def list_sources(brand_id: str, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    _get_brand_scoped(brand_id, db, current_user.org_id)
    sources = (
        db.query(BrandKnowledgeSource)
        .filter(BrandKnowledgeSource.brand_id == brand_id)
        .order_by(BrandKnowledgeSource.created_at.desc())
        .all()
    )
    return {"items": [_source_to_dict(s) for s in sources], "total": len(sources)}


# ---------------------------------------------------------------------------
# POST /v1/brands/:id/sources
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def add_source(
    brand_id: str,
    body: AddSourceIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)

    if brand.status not in ("DRAFT", "PENDING_REVIEW"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot add sources when brand status is {brand.status}",
        )

    allowed_types = {"manual_text", "uploaded_doc"}
    if body.source_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"source_type must be one of {allowed_types}",
        )

    if body.source_type == "manual_text" and not body.raw_text:
        raise HTTPException(status_code=422, detail="raw_text is required for manual_text sources")
    if body.source_type == "uploaded_doc" and not body.storage_key:
        raise HTTPException(status_code=422, detail="storage_key is required for uploaded_doc sources")

    raw_text = body.raw_text or ""
    normalized = " ".join(raw_text.split())

    now = datetime.now(timezone.utc)
    source = BrandKnowledgeSource(
        id=uuid_str(),
        brand_id=brand_id,
        source_type=body.source_type,
        title=body.title,
        url=None,
        storage_key=body.storage_key,
        raw_text=raw_text or None,
        normalized_text=normalized or body.storage_key or "",
        metadata_json=body.metadata,
        word_count=len(normalized.split()) if normalized else 0,
        fetched_at=now,
        purge_at=None,
    )
    db.add(source)

    db.add(AuditLog(
        org_id=brand.org_id,
        user_id=current_user.id,
        brand_id=brand_id,
        action="brand.source_added",
        resource_type="brand_knowledge_source",
        resource_id=source.id,
        metadata_json={"source_type": body.source_type, "title": body.title},
    ))

    db.commit()
    return {"source_id": source.id, "ingest_job_id": None}  # ingest job wiring added when worker is up


# ---------------------------------------------------------------------------
# POST /v1/brands/:id/sources/reingest — re-embed existing sources + DNA into Pinecone
# ---------------------------------------------------------------------------

@router.post("/reingest", status_code=202)
def reingest_sources(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Re-run the embedding/ingest stage for a brand's existing knowledge sources.

    Idempotent (the ingest clears the namespace first). Use this to backfill brands
    whose vectors never landed, without re-crawling/re-extracting.
    """
    brand = _get_brand_scoped(brand_id, db, current_user.org_id)

    sources_count = (
        db.query(BrandKnowledgeSource)
        .filter(BrandKnowledgeSource.brand_id == brand_id)
        .count()
    )
    if sources_count == 0:
        raise HTTPException(status_code=400, detail="No knowledge sources to ingest")

    job = Job(
        id=uuid_str(),
        org_id=brand.org_id,
        brand_id=brand_id,
        job_type="reingest",
        status="QUEUED",
        stage="INGEST",
        input_payload={"brand_id": brand_id},
    )
    db.add(job)
    db.add(AuditLog(
        org_id=brand.org_id,
        user_id=current_user.id,
        brand_id=brand_id,
        action="brand.reingest_requested",
        resource_type="job",
        resource_id=job.id,
        metadata_json={"sources_count": sources_count},
    ))
    db.commit()

    JobDispatcher().enqueue_reingest(job_id=job.id, brand_id=brand_id)
    return {"job_id": job.id, "sources_count": sources_count}
