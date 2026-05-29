from sqlalchemy.orm import Session

from app.models import Brand, Job


def get_brand(db: Session, brand_id: str, org_id: str) -> Brand | None:
    return db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == org_id).first()


def list_brands(db: Session, org_id: str) -> list[Brand]:
    return db.query(Brand).filter(Brand.org_id == org_id).order_by(Brand.created_at.desc()).all()


def get_active_job(db: Session, brand_id: str) -> Job | None:
    return (
        db.query(Job)
        .filter(Job.brand_id == brand_id, Job.status.in_(["QUEUED", "NEW", "RUNNING"]))
        .order_by(Job.created_at.desc())
        .first()
    )
