from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog, Brand, Job
from tests.conftest import FakeQueue, auth_headers, create_user


def create_manual_brand(client: TestClient, db_session: Session) -> tuple[Brand, dict[str, str]]:
    user = create_user(db_session, "delete-brand@example.com", plan_code="pro")
    headers = auth_headers(user)
    response = client.post(
        "/v1/brands",
        headers=headers,
        json={"name": "Delete Me", "dna_source": "manual"},
    )
    assert response.status_code == 201
    brand = db_session.query(Brand).filter_by(id=response.json()["brand_id"]).one()
    return brand, headers


def test_delete_brand_immediately(
    client: TestClient,
    db_session: Session,
) -> None:
    brand, headers = create_manual_brand(client, db_session)
    brand_id = brand.id

    response = client.delete(f"/v1/brands/{brand.id}", headers=headers)

    # Brand deletion is now immediate
    assert response.status_code == 204
    assert not response.content  # No content for 204
    
    # Brand should be completely deleted
    deleted_brand = db_session.query(Brand).filter_by(id=brand_id).first()
    assert deleted_brand is None
    
    # No purge jobs should be created
    purge_jobs = db_session.query(Job).filter_by(job_type="brand.purge").all()
    assert len(purge_jobs) == 0


def test_delete_nonexistent_brand_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    brand, headers = create_manual_brand(client, db_session)
    brand_id = brand.id

    first_response = client.delete(f"/v1/brands/{brand_id}", headers=headers)
    second_response = client.delete(f"/v1/brands/{brand_id}", headers=headers)

    assert first_response.status_code == 204
    assert second_response.status_code == 404  # Brand no longer exists


def test_delete_writes_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    brand, headers = create_manual_brand(client, db_session)
    brand_id = brand.id
    brand_name = brand.name

    response = client.delete(f"/v1/brands/{brand.id}", headers=headers)

    assert response.status_code == 204
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.brand_id == brand_id, AuditLog.action == "brand.deleted")
        .one()
    )
    assert audit.resource_type == "brand"
    assert audit.resource_id == brand_id
    assert audit.metadata_json["brand_name"] == brand_name

