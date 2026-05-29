from collections.abc import Generator
from dataclasses import dataclass, field
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.jwt import create_access_token
from app.db import get_db
from app.main import app
from app.models import Base, Organization, User


@dataclass
class EnqueuedCall:
    func: str
    kwargs: dict[str, Any]
    job_id: str | None = None
    queue: str = "default"


@dataclass
class FakeQueue:
    name: str
    calls: list[EnqueuedCall] = field(default_factory=list)

    def enqueue(
        self,
        func: str,
        *,
        kwargs: dict[str, Any],
        job_id: str | None = None,
        **_: Any,
    ):
        # Accept and ignore other RQ kwargs (e.g. `retry`) so test stubbing
        # doesn't have to track upstream API changes.
        self.calls.append(EnqueuedCall(func=func, kwargs=kwargs, job_id=job_id, queue=self.name))
        return type("FakeJob", (), {"id": job_id or "fake"})()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
    else:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_user(session: Session, email: str, role: str = "admin") -> User:
    org = Organization(name=f"Org for {email}")
    session.add(org)
    session.flush()
    user = User(email=email, password_hash="test", name=email, role=role, org_id=org.id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def fake_queues(monkeypatch: pytest.MonkeyPatch) -> dict[str, FakeQueue]:
    queues: dict[str, FakeQueue] = {}

    def get_fake_queue(name: str) -> FakeQueue:
        return queues.setdefault(name, FakeQueue(name=name))

    monkeypatch.setattr("app.queue.get_queue", get_fake_queue)
    return queues
