from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    org_id: str,
    action: str,
    user_id: str | None = None,
    brand_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        org_id=org_id,
        user_id=user_id,
        brand_id=brand_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
    )
    db.add(log)
    return log

