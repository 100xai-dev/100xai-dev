from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuditLog, Brand, Job
from tests.conftest import FakeQueue, auth_headers, create_user


def create_manual_brand(client: TestClient, db_session: Session) -> tuple[Brand, dict[str, str]]:
    user = create_user(db_session, "delete-brand@example.com")
    headers = auth_headers(user)
    response = client.post(
        "/v1/brands",
        headers=headers,
        json={"name": "Delete Me", "dna_source": "manual"},
    )
    assert response.status_code == 201
    brand = db_session.query(Brand).filter_by(id=response.json()["brand_id"]).one()
    return brand, headers


def test_delete_sets_pending_delete_and_enqueues_purge(
    client: TestClient,
    db_session: Session,
    fake_queues: dict[str, FakeQueue],
) -> None:
    brand, headers = create_manual_brand(client, db_session)

    response = client.delete(f"/v1/brands/{brand.id}", headers=headers)

    assert response.status_code == 202
    assert response.json()["job_id"]
    db_session.refresh(brand)
    assert brand.status == "PENDING_DELETE"

    job = db_session.query(Job).filter_by(id=response.json()["job_id"]).one()
    assert job.job_type == "brand.purge"
    assert job.status == "QUEUED"

    purge = fake_queues["purge"]
    assert len(purge.calls) == 1
    assert purge.calls[0].func == "worker.tasks.purge.purge_brand"
    assert purge.calls[0].kwargs == {"job_id": job.id, "brand_id": brand.id}


def test_delete_idempotent_returns_409(
    client: TestClient,
    db_session: Session,
    fake_queues: dict[str, FakeQueue],
) -> None:
    brand, headers = create_manual_brand(client, db_session)

    first_response = client.delete(f"/v1/brands/{brand.id}", headers=headers)
    second_response = client.delete(f"/v1/brands/{brand.id}", headers=headers)

    assert first_response.status_code == 202
    assert second_response.status_code == 409
    assert len(fake_queues["purge"].calls) == 1


def test_delete_writes_audit_log(
    client: TestClient,
    db_session: Session,
    fake_queues: dict[str, FakeQueue],
) -> None:
    brand, headers = create_manual_brand(client, db_session)

    response = client.delete(f"/v1/brands/{brand.id}", headers=headers)

    assert response.status_code == 202
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.brand_id == brand.id, AuditLog.action == "brand.delete_requested")
        .one()
    )
    assert audit.resource_type == "brand"
    assert audit.resource_id == brand.id

