from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Per-request session that commits on success and rolls back on exception.

    Services should `flush()` to materialize IDs; the commit happens here once
    the handler returns successfully. Callers that need commit-before-enqueue
    (so the DB row exists when the queue worker dequeues) must commit
    explicitly inside the service — see brand_service.create_brand.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
