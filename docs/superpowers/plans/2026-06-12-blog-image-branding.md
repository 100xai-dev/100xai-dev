# Blog Featured Image Opt-In + Brand Logo Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When creating a blog, the user chooses whether the article gets a featured image; when it does, the generated image is stamped with the brand's logo before being attached to the draft.

**Architecture:** A new `include_image` boolean rides the existing pipeline payload chain (blogs router → P1 keyword-research job → P2 SERP analysis → P3 content generation) and gates the existing `generate_featured_image()` call. The logo itself is stored as a new `logo_url` column on `brand_profiles` (a URL the user sets in the Brand DNA editor). Branding is done deterministically with a Pillow overlay (generative models cannot reproduce exact logos), and the composited JPEG is uploaded to the S3-compatible MinIO service that already exists in `docker-compose.yml` but was never wired into the backend. Every branding step fails soft: no logo / no S3 / download failure → the unbranded Leonardo image is used, exactly as today.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), RQ worker pipelines, Pillow (new), boto3 (new) against MinIO/S3, Next.js + TypeScript (frontend), pytest with the in-memory SQLite `conftest.py` fixtures.

**Pre-existing context an implementer needs:**
- The user-facing "Generate blog" flow: `frontend/app/brands/[id]/blogs/new/page.tsx` → `createBlogJob()` in `frontend/lib/api.ts` → `POST /v1/brands/{brand_id}/blogs` in `backend/app/routers/blogs.py` (`create_blog_job`, line 49). That endpoint creates a `keyword_research` `Job` whose `input_payload` is the source of truth that later pipeline stages read.
- P1→P3 payload propagation happens in `backend/app/services/seo_research.py` in **two** places: `_trigger_content_generation_directly()` (~line 906, the few-keywords fallback) and the auto-trigger block inside the SERP pipeline (~line 1740). Both build a `content_payload` dict for the P3 job.
- P3 is `backend/app/services/content_generation.py`. `run_content_generation_pipeline()` calls `generate_featured_image()` at step 11 (~line 1836). `generate_featured_image()` (line 1610) does Leonardo generation → optional Placid composite → `store_image_in_bucket()` (which is a stub that returns the input URL unchanged).
- Brand profile model: `BrandProfile` in `backend/app/models/onboarding.py` (line 33). Schemas: `backend/app/schemas/brand_profile.py`. Patch endpoint: `PATCH /v1/brands/{brand_id}/profile` → `patch_profile()` in `backend/app/services/brand_service.py` (only allowed while brand status is `PENDING_REVIEW` and profile not locked).
- Frontend profile editor: `frontend/components/brand/profile-editor.tsx` (rendered on `frontend/app/brands/[id]/dna/page.tsx`).
- Tests run from `backend/` with its venv: `cd backend && venv/bin/python -m pytest tests/<file> -v`. Fixtures in `backend/tests/conftest.py`: `client` (TestClient with sqlite in-memory DB), `db_session`, `fake_queues`, plus helpers `create_user()` / `auth_headers()`.
- Latest alembic revision is `20260609_0011` (`backend/alembic/versions/20260609_0011_billing.py`).
- The repo is on branch `feat/email-verification-razorpay-terms` with unrelated uncommitted changes in `frontend/`. Do not commit those files; stage only the files listed in each task.

---

### Task 1: `logo_url` column on brand profiles (model + migration + schemas + API)

**Files:**
- Modify: `backend/app/models/onboarding.py` (BrandProfile, after line 59 `visual_direction`)
- Create: `backend/alembic/versions/20260612_0012_brand_profile_logo_url.py`
- Modify: `backend/app/schemas/brand_profile.py` (BrandProfileContent + BrandProfilePatch)
- Test: `backend/tests/test_brand_logo.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_brand_logo.py`:

```python
"""Tests for the brand logo_url profile field."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand, BrandProfile
from tests.conftest import auth_headers, create_user


def _reviewable_brand(db: Session, user) -> Brand:
    """Brand in PENDING_REVIEW with an unlocked profile (patchable state)."""
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="PENDING_REVIEW",
        created_by=user.id,
    )
    db.add(brand)
    db.flush()
    db.add(BrandProfile(
        brand_id=brand.id,
        name="Acme",
        one_liner="We make robots for warehouses.",
        tone_rules="Friendly and concrete.",
        unique_angle="Spatial robotics.",
        generation_source="manual",
    ))
    db.commit()
    return brand


def test_patch_profile_sets_logo_url(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "logo-admin@example.com")
    brand = _reviewable_brand(db_session, user)

    resp = client.patch(
        f"/v1/brands/{brand.id}/profile",
        headers=auth_headers(user),
        json={"logo_url": "https://acme.example/logo.png"},
    )
    assert resp.status_code == 200
    assert resp.json()["logo_url"] == "https://acme.example/logo.png"

    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    assert profile.logo_url == "https://acme.example/logo.png"


def test_patch_profile_clears_logo_url(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "logo-clear@example.com")
    brand = _reviewable_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/old-logo.png"
    db_session.commit()

    resp = client.patch(
        f"/v1/brands/{brand.id}/profile",
        headers=auth_headers(user),
        json={"logo_url": None},
    )
    assert resp.status_code == 200
    assert resp.json()["logo_url"] is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_brand_logo.py -v`
Expected: FAIL — `BrandProfile` has no attribute `logo_url` (TypeError on construction or AttributeError), and/or response JSON has no `logo_url` key.

- [ ] **Step 3: Add the model column**

In `backend/app/models/onboarding.py`, inside `class BrandProfile`, directly after the `visual_direction` line (line 59):

```python
    visual_direction: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String)
```

(The first line already exists — add only the `logo_url` line under it.)

- [ ] **Step 4: Add the schema fields**

In `backend/app/schemas/brand_profile.py`:

In `BrandProfileContent`, after `visual_direction: str | None = None`:

```python
    logo_url: HttpUrl | None = None
```

In `BrandProfilePatch`, after `visual_direction: str | None = None`:

```python
    logo_url: HttpUrl | None = None
```

`HttpUrl` is already imported in this file. `BrandProfileFull` inherits from `BrandProfileContent`, so the response schema picks it up automatically. `patch_profile()` uses `model_dump(exclude_unset=True, mode="json")`, which serialises `HttpUrl` to `str`, so no service change is needed.

Note on patch semantics: `exclude_unset=True` means sending `{"logo_url": null}` explicitly clears the field (test 2 covers this), while omitting it leaves it untouched.

- [ ] **Step 5: Create the alembic migration**

Create `backend/alembic/versions/20260612_0012_brand_profile_logo_url.py`:

```python
"""Add logo_url to brand_profiles

Revision ID: 20260612_0012
Revises: 20260609_0011
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20260612_0012"
down_revision = "20260609_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("brand_profiles", sa.Column("logo_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("brand_profiles", "logo_url")
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_brand_logo.py -v`
Expected: 2 PASSED (the sqlite test DB is built from `Base.metadata`, so the model change is enough; the migration is for the real Postgres DB).

- [ ] **Step 7: Apply the migration to the dev database**

Run: `cd backend && venv/bin/alembic upgrade head`
Expected: `Running upgrade 20260609_0011 -> 20260612_0012`

- [ ] **Step 8: Run the full backend suite to check for regressions**

Run: `cd backend && venv/bin/python -m pytest tests/ -x -q`
Expected: all tests pass (same pass/fail set as before this task).

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/onboarding.py backend/app/schemas/brand_profile.py "backend/alembic/versions/20260612_0012_brand_profile_logo_url.py" backend/tests/test_brand_logo.py
git commit -m "feat: add logo_url to brand profiles"
```

---

### Task 2: S3/MinIO storage service

The compose stack already runs MinIO and passes `S3_ENDPOINT_URL` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` env vars to the backend, but `Settings` only reads `s3_bucket` and nothing in the code talks to S3. This task adds the missing settings, dependencies, and a small upload helper.

**Files:**
- Modify: `backend/app/config.py` (Settings, around line 40 where `s3_bucket` lives)
- Modify: `backend/requirements.txt`
- Modify: `docker-compose.yml` (backend `environment` block, after line 13 `S3_BUCKET`)
- Create: `backend/app/services/storage.py`
- Test: `backend/tests/test_storage.py`

- [ ] **Step 1: Add dependencies**

Append to `backend/requirements.txt`:

```
boto3>=1.34.0
Pillow>=10.3.0
```

Install: `cd backend && venv/bin/pip install "boto3>=1.34.0" "Pillow>=10.3.0"`
Expected: `Successfully installed ...` (or already satisfied).

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_storage.py`:

```python
"""Tests for the S3/MinIO storage helper."""

import pytest

from app.services import storage


class FakeS3Client:
    def __init__(self):
        self.put_calls = []
        self.bucket_created = False

    def head_bucket(self, Bucket):
        raise Exception("no such bucket")

    def create_bucket(self, Bucket):
        self.bucket_created = True

    def put_bucket_policy(self, Bucket, Policy):
        self.policy = Policy

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append(
            {"Bucket": Bucket, "Key": Key, "Body": Body, "ContentType": ContentType}
        )


class FakeSettings:
    s3_endpoint_url = "http://minio:9000"
    s3_access_key = "test-key"
    s3_secret_key = "test-secret"
    s3_bucket = "test-bucket"
    s3_public_url = "http://localhost:9000"


def test_upload_public_image_puts_object_and_returns_public_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeS3Client()
    monkeypatch.setattr(storage, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(storage, "_make_client", lambda settings: fake)

    url = storage.upload_public_image("branded/job1-featured.jpg", b"jpegbytes")

    assert fake.bucket_created is True
    assert len(fake.put_calls) == 1
    call = fake.put_calls[0]
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == "branded/job1-featured.jpg"
    assert call["Body"] == b"jpegbytes"
    assert call["ContentType"] == "image/jpeg"
    assert url == "http://localhost:9000/test-bucket/branded/job1-featured.jpg"


def test_upload_public_image_raises_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Unconfigured(FakeSettings):
        s3_endpoint_url = None
        s3_access_key = None
        s3_secret_key = None

    monkeypatch.setattr(storage, "get_settings", lambda: Unconfigured())

    with pytest.raises(storage.StorageNotConfigured):
        storage.upload_public_image("k.jpg", b"x")
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.storage'` (or ImportError).

- [ ] **Step 4: Add settings fields**

In `backend/app/config.py`, replace the single line `s3_bucket: str = "100xai-uploads"` (line 40) with:

```python
    s3_bucket: str = "100xai-uploads"
    s3_endpoint_url: str | None = None  # e.g. http://minio:9000 (compose) / AWS default if None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    # Base URL browsers/publishers can reach the bucket on. Inside docker the
    # endpoint is http://minio:9000 (service DNS) but the public URL is
    # http://localhost:9000 — they differ, hence two settings.
    s3_public_url: str | None = None
```

(Pydantic-settings maps these from the `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_PUBLIC_URL` env vars automatically.)

- [ ] **Step 5: Add the public URL env var to docker-compose**

In `docker-compose.yml`, in the backend service `environment` block, after the `S3_BUCKET` line (line 13), add:

```yaml
      S3_PUBLIC_URL: ${S3_PUBLIC_URL:-http://localhost:9000}
```

- [ ] **Step 6: Implement the storage service**

Create `backend/app/services/storage.py`:

```python
"""Thin S3-compatible storage helper (MinIO in dev, any S3 in prod).

Used for hosting images the backend produces itself (e.g. logo-branded
featured images). Uploads are public-read: the URLs are embedded in blog
posts and fetched by external publishers (WordPress, Ghost, ...).
"""

import json
import logging

import boto3
from botocore.client import Config

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageNotConfigured(Exception):
    """Raised when S3 credentials/endpoint are missing from settings."""


def _make_client(settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _ensure_public_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }],
        }
        try:
            client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        except Exception as exc:
            logger.warning("Could not set public-read policy on %s: %s", bucket, exc)


def upload_public_image(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload image bytes and return a publicly reachable URL."""
    settings = get_settings()
    if not (settings.s3_endpoint_url and settings.s3_access_key and settings.s3_secret_key):
        raise StorageNotConfigured("S3_ENDPOINT_URL / S3_ACCESS_KEY / S3_SECRET_KEY not set")

    client = _make_client(settings)
    _ensure_public_bucket(client, settings.s3_bucket)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    base = (settings.s3_public_url or settings.s3_endpoint_url).rstrip("/")
    return f"{base}/{settings.s3_bucket}/{key}"
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_storage.py -v`
Expected: 2 PASSED.

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/requirements.txt docker-compose.yml backend/app/services/storage.py backend/tests/test_storage.py
git commit -m "feat: add S3/MinIO storage helper for backend-produced images"
```

---

### Task 3: Logo overlay service (Pillow)

Deterministic compositing: scale the logo to ~18% of the image width, paste it bottom-right with a margin, respecting the logo's alpha channel. A generative model is never asked to draw the logo.

**Files:**
- Create: `backend/app/services/image_branding.py`
- Test: `backend/tests/test_image_branding.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_image_branding.py`:

```python
"""Tests for the logo-overlay image branding service."""

import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.services import image_branding


def _png_bytes(size, color) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, "PNG")
    return buf.getvalue()


def test_overlay_logo_keeps_size_and_stamps_bottom_right() -> None:
    base = _png_bytes((1024, 576), (10, 10, 10, 255))      # near-black 16:9 base
    logo = _png_bytes((400, 200), (255, 0, 0, 255))        # solid red logo

    out = image_branding.overlay_logo(base, logo)

    img = Image.open(BytesIO(out))
    assert img.format == "JPEG"
    assert img.size == (1024, 576)
    # A pixel inside the bottom-right stamp area is now red-ish, not black.
    r, g, b = img.convert("RGB").getpixel((1024 - 60, 576 - 60))
    assert r > 150 and g < 100 and b < 100
    # The top-left corner is untouched.
    r2, g2, b2 = img.convert("RGB").getpixel((20, 20))
    assert r2 < 60 and g2 < 60 and b2 < 60


def test_overlay_logo_respects_transparency() -> None:
    base = _png_bytes((1000, 500), (10, 10, 10, 255))
    logo = _png_bytes((300, 150), (0, 255, 0, 0))  # fully transparent logo

    out = image_branding.overlay_logo(base, logo)

    img = Image.open(BytesIO(out)).convert("RGB")
    # Transparent logo leaves the bottom-right corner dark.
    r, g, b = img.getpixel((1000 - 50, 500 - 50))
    assert r < 60 and g < 60 and b < 60


def test_brand_featured_image_returns_none_on_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url):
            raise RuntimeError("network down")

    monkeypatch.setattr(image_branding.httpx, "AsyncClient", FailingClient)

    result = asyncio.run(image_branding.brand_featured_image(
        "https://cdn.example/img.jpg",
        "https://acme.example/logo.png",
        "branded/x.jpg",
    ))
    assert result is None


def test_brand_featured_image_overlays_and_uploads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _png_bytes((640, 360), (10, 10, 10, 255))
    logo = _png_bytes((100, 50), (255, 0, 0, 255))
    responses = {
        "https://cdn.example/img.jpg": base,
        "https://acme.example/logo.png": logo,
    }

    class FakeResponse:
        def __init__(self, content): self.content = content
        def raise_for_status(self): ...

    class FakeClient:
        def __init__(self, *a, **kw): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url): return FakeResponse(responses[url])

    uploaded = {}

    def fake_upload(key, data, content_type="image/jpeg"):
        uploaded["key"] = key
        uploaded["data"] = data
        return f"http://localhost:9000/test-bucket/{key}"

    monkeypatch.setattr(image_branding.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(image_branding, "upload_public_image", fake_upload)

    result = asyncio.run(image_branding.brand_featured_image(
        "https://cdn.example/img.jpg",
        "https://acme.example/logo.png",
        "branded/job1-featured.jpg",
    ))

    assert result == "http://localhost:9000/test-bucket/branded/job1-featured.jpg"
    assert uploaded["key"] == "branded/job1-featured.jpg"
    stamped = Image.open(BytesIO(uploaded["data"])).convert("RGB")
    r, g, b = stamped.getpixel((640 - 40, 360 - 40))
    assert r > 150  # red logo landed bottom-right
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_image_branding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.image_branding'`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/image_branding.py`:

```python
"""Stamp a brand logo onto generated featured images.

The overlay is deterministic (Pillow), not generative: image models cannot
faithfully reproduce an exact logo, so the logo is composited after
generation. The branded JPEG is uploaded to S3/MinIO via the storage
service. Every step fails soft — callers fall back to the unbranded image
when this module returns None.
"""

import logging
from io import BytesIO

import httpx
from PIL import Image

from app.services.storage import upload_public_image

logger = logging.getLogger(__name__)

# Logo width as a fraction of the base image width, and the margin from the
# bottom-right corner as a fraction of the base width.
LOGO_WIDTH_RATIO = 0.18
MARGIN_RATIO = 0.04


def overlay_logo(base_bytes: bytes, logo_bytes: bytes) -> bytes:
    """Paste the logo bottom-right onto the base image; return JPEG bytes."""
    base = Image.open(BytesIO(base_bytes)).convert("RGB")
    logo = Image.open(BytesIO(logo_bytes)).convert("RGBA")

    target_width = max(1, int(base.width * LOGO_WIDTH_RATIO))
    scale = target_width / logo.width
    target_height = max(1, int(logo.height * scale))
    logo = logo.resize((target_width, target_height), Image.LANCZOS)

    margin = int(base.width * MARGIN_RATIO)
    position = (base.width - logo.width - margin, base.height - logo.height - margin)
    base.paste(logo, position, logo)  # third arg = alpha mask

    out = BytesIO()
    base.save(out, "JPEG", quality=90)
    return out.getvalue()


async def brand_featured_image(image_url: str, logo_url: str, key: str) -> str | None:
    """Download image + logo, overlay, upload; return the hosted URL or None."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            logo_resp = await client.get(logo_url)
            logo_resp.raise_for_status()

        branded = overlay_logo(img_resp.content, logo_resp.content)
        # boto3 is sync; acceptable here — this runs inside an RQ worker task,
        # not the API event loop.
        return upload_public_image(key, branded)
    except Exception as exc:
        logger.warning("Logo branding failed (%s); falling back to unbranded image", exc)
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_image_branding.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_branding.py backend/tests/test_image_branding.py
git commit -m "feat: add Pillow logo-overlay branding for featured images"
```

---

### Task 4: `include_image` flag through the pipeline (backend)

**Files:**
- Modify: `backend/app/schemas/blog.py` (BlogJobCreate, line 5)
- Modify: `backend/app/routers/blogs.py` (create_blog_job input_payload, ~line 100)
- Modify: `backend/app/services/seo_research.py` (both content_payload sites, ~line 924 and ~line 1744)
- Modify: `backend/app/services/content_generation.py` (step-11 gate, ~line 1836)
- Test: `backend/tests/test_blog_image_flag.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_blog_image_flag.py`:

```python
"""Tests for the include_image flag flowing through the blog pipeline."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand, BrandProfile, Job
from app.services.seo_research import _trigger_content_generation_directly
from tests.conftest import FakeQueue, auth_headers, create_user


def _ready_brand(db: Session, user) -> Brand:
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="READY",
        created_by=user.id,
    )
    db.add(brand)
    db.flush()
    db.add(BrandProfile(
        brand_id=brand.id,
        name="Acme",
        one_liner="We make robots for warehouses.",
        tone_rules="Friendly and concrete.",
        unique_angle="Spatial robotics.",
        generation_source="manual",
    ))
    db.commit()
    return brand


def test_create_blog_job_stores_include_image_false(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-flag@example.com")
    brand = _ready_brand(db_session, user)

    resp = client.post(
        f"/v1/brands/{brand.id}/blogs",
        headers=auth_headers(user),
        json={"keyword": "warehouse robots", "include_image": False},
    )
    assert resp.status_code == 201

    job = db_session.query(Job).filter(Job.id == resp.json()["id"]).first()
    assert job.input_payload["include_image"] is False


def test_create_blog_job_defaults_include_image_true(
    client: TestClient, db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-default@example.com")
    brand = _ready_brand(db_session, user)

    resp = client.post(
        f"/v1/brands/{brand.id}/blogs",
        headers=auth_headers(user),
        json={"keyword": "warehouse robots"},
    )
    assert resp.status_code == 201

    job = db_session.query(Job).filter(Job.id == resp.json()["id"]).first()
    assert job.input_payload["include_image"] is True


def test_direct_content_trigger_propagates_include_image(
    db_session: Session, fake_queues: dict[str, FakeQueue]
) -> None:
    user = create_user(db_session, "img-prop@example.com")
    brand = _ready_brand(db_session, user)

    parent = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="keyword_research",
        status="RUNNING",
        stage="KEYWORD",
        input_payload={
            "keyword": "warehouse robots",
            "blog_job_id": "blog-1",
            "include_image": False,
        },
    )
    db_session.add(parent)
    db_session.commit()

    _trigger_content_generation_directly(
        db_session, parent, "warehouse robots", parent.input_payload
    )

    content_job = db_session.query(Job).filter(
        Job.job_type == "content_generation"
    ).first()
    assert content_job is not None
    assert content_job.input_payload["include_image"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_blog_image_flag.py -v`
Expected: first two tests FAIL on `assert ... is False` / `KeyError: 'include_image'`; third FAILS on the missing payload key. (`include_image` in the POST body is silently ignored until the schema knows it.)

- [ ] **Step 3: Add the schema field**

In `backend/app/schemas/blog.py`, change `BlogJobCreate`:

```python
class BlogJobCreate(BaseModel):
    keyword: str
    include_image: bool = True
```

- [ ] **Step 4: Store the flag in the pipeline job payload**

In `backend/app/routers/blogs.py`, in `create_blog_job`, extend the `input_payload` dict of the `pipeline_job` (currently ends with `"blog_integration": True,` around line 105):

```python
        input_payload={
            "keyword": keyword,
            "created_by": current_user.id,
            "blog_job_id": job_id,     # Link the final draft back to this BlogJob.
            "blog_integration": True,  # Flag: originated from the blog UI.
            "include_image": payload.include_image,
        },
```

- [ ] **Step 5: Propagate at content-job spawn site 1**

In `backend/app/services/seo_research.py`, in `_trigger_content_generation_directly()` (~line 924), extend `content_payload`:

```python
    content_payload = {
        "keyword": keyword,
        "auto_triggered": True,
        "skipped_serp": True,
        "created_by": parent_payload.get("created_by", "system"),
        "blog_job_id": parent_payload.get("blog_job_id"),
        "blog_integration": True,
        "include_image": parent_payload.get("include_image", True),
    }
```

- [ ] **Step 6: Propagate at content-job spawn site 2**

In `backend/app/services/seo_research.py`, in the auto-trigger block (~line 1744), extend the other `content_payload`:

```python
                        content_payload = {
                            "keyword": top_keyword,
                            "serp_analysis_job_id": job_id,
                            "auto_triggered": True,
                            "triggered_at": str(db.scalar(text("SELECT NOW()"))),
                            "created_by": parent_payload.get("created_by", "system"),
                            "include_image": parent_payload.get("include_image", True),
                        }
```

- [ ] **Step 7: Gate image generation in Pipeline 3**

In `backend/app/services/content_generation.py`, in `run_content_generation_pipeline()` (~line 1836), replace:

```python
        # 11. Generate featured image (non-blocking)
        logger.info("Starting image generation...")
        image_url = await generate_featured_image(final_article, brand_profile, job, db)
        
        if image_url:
            draft.featured_image_url = image_url
            logger.info(f"Featured image generated: {image_url}")
        else:
            logger.warning("Image generation failed, article will be published without featured image")
```

with:

```python
        # 11. Generate featured image (non-blocking, user opt-in)
        include_image = (job.input_payload or {}).get("include_image", True)
        if include_image:
            logger.info("Starting image generation...")
            image_url = await generate_featured_image(final_article, brand_profile, job, db)

            if image_url:
                draft.featured_image_url = image_url
                logger.info(f"Featured image generated: {image_url}")
            else:
                logger.warning("Image generation failed, article will be published without featured image")
        else:
            logger.info("Image generation skipped — include_image=False on this job")
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_blog_image_flag.py tests/test_blog_pipeline.py -v`
Expected: all PASS (including the pre-existing pipeline tests — the new payload key must not break them).

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/blog.py backend/app/routers/blogs.py backend/app/services/seo_research.py backend/app/services/content_generation.py backend/tests/test_blog_image_flag.py
git commit -m "feat: add include_image opt-in flag through the blog pipeline"
```

---

### Task 5: Stamp the logo inside `generate_featured_image`

**Files:**
- Modify: `backend/app/services/content_generation.py` (`generate_featured_image`, lines 1610–1664)
- Test: `backend/tests/test_blog_image_flag.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_blog_image_flag.py`:

```python
def test_generate_featured_image_brands_when_logo_set(
    db_session: Session, monkeypatch
) -> None:
    import asyncio

    from app.services import content_generation

    user = create_user(db_session, "img-brand@example.com")
    brand = _ready_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/logo.png"
    db_session.commit()

    job = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="content_generation",
        status="RUNNING",
        stage="CONTENT",
        input_payload={"keyword": "warehouse robots"},
    )
    db_session.add(job)
    db_session.commit()

    class FakeArticle:
        meta_title = "Warehouse Robots Guide"

    async def fake_prompt(article, brand_profile):
        return {"Complete_Prompt": "robots in a warehouse"}

    class FakeLeonardo:
        async def generate_image(self, prompt):
            return "https://cdn.leonardo.example/raw.jpg"

    async def fake_brand(image_url, logo_url, key):
        assert image_url == "https://cdn.leonardo.example/raw.jpg"
        assert logo_url == "https://acme.example/logo.png"
        return "http://localhost:9000/bucket/branded.jpg"

    monkeypatch.setattr(content_generation, "generate_image_prompt", fake_prompt)
    monkeypatch.setattr(content_generation, "LeonardoService", FakeLeonardo)
    monkeypatch.setattr(content_generation, "brand_featured_image", fake_brand)

    url = asyncio.run(content_generation.generate_featured_image(
        FakeArticle(), profile, job, db_session
    ))
    assert url == "http://localhost:9000/bucket/branded.jpg"


def test_generate_featured_image_falls_back_when_branding_fails(
    db_session: Session, monkeypatch
) -> None:
    import asyncio

    from app.services import content_generation

    user = create_user(db_session, "img-fallback@example.com")
    brand = _ready_brand(db_session, user)
    profile = db_session.query(BrandProfile).filter(
        BrandProfile.brand_id == brand.id
    ).first()
    profile.logo_url = "https://acme.example/logo.png"
    db_session.commit()

    job = Job(
        org_id=user.org_id,
        brand_id=brand.id,
        job_type="content_generation",
        status="RUNNING",
        stage="CONTENT",
        input_payload={"keyword": "warehouse robots"},
    )
    db_session.add(job)
    db_session.commit()

    class FakeArticle:
        meta_title = "Warehouse Robots Guide"

    async def fake_prompt(article, brand_profile):
        return {"Complete_Prompt": "robots in a warehouse"}

    class FakeLeonardo:
        async def generate_image(self, prompt):
            return "https://cdn.leonardo.example/raw.jpg"

    async def fake_brand(image_url, logo_url, key):
        return None  # branding failed (e.g. S3 not configured)

    monkeypatch.setattr(content_generation, "generate_image_prompt", fake_prompt)
    monkeypatch.setattr(content_generation, "LeonardoService", FakeLeonardo)
    monkeypatch.setattr(content_generation, "brand_featured_image", fake_brand)

    url = asyncio.run(content_generation.generate_featured_image(
        FakeArticle(), profile, job, db_session
    ))
    assert url == "https://cdn.leonardo.example/raw.jpg"
```

Note: these tests rely on `generate_featured_image` referencing `brand_featured_image` as a module-level name in `content_generation` (imported there in Step 3), so monkeypatching `content_generation.brand_featured_image` works. The existing `store_image_in_bucket` stub returns its input URL unchanged, which is why the fallback test expects the raw Leonardo URL.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_blog_image_flag.py -v`
Expected: the two new tests FAIL — `AttributeError: ... has no attribute 'brand_featured_image'` on the monkeypatch line.

- [ ] **Step 3: Wire branding into `generate_featured_image`**

In `backend/app/services/content_generation.py`:

Add the import near the other service imports at the top of the file:

```python
from app.services.image_branding import brand_featured_image
```

In `generate_featured_image()` (line 1610), after the Placid block and **before** the `store_image_in_bucket` call (i.e. directly after the `final_image_url = raw_image_url` fallback at line 1649), insert:

```python
        # Stamp the brand logo (deterministic Pillow overlay). Fails soft:
        # branding returning None keeps the unbranded image.
        if brand_profile.logo_url:
            branded_url = await brand_featured_image(
                final_image_url,
                brand_profile.logo_url,
                f"branded/{job.id}-featured.jpg",
            )
            if branded_url:
                final_image_url = branded_url
            else:
                logger.warning("Logo branding failed for job %s; using unbranded image", job.id)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_blog_image_flag.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/bin/python -m pytest tests/ -x -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/content_generation.py backend/tests/test_blog_image_flag.py
git commit -m "feat: stamp brand logo onto generated featured images"
```

---

### Task 6: Frontend — logo field in Brand DNA editor + image opt-in on the new-blog form

**Files:**
- Modify: `frontend/lib/types.ts` (BrandProfileContent, ~line 185)
- Modify: `frontend/components/brand/profile-editor.tsx` (NULLABLE_STRING_FIELDS + form input)
- Modify: `frontend/lib/api.ts` (`createBlogJob`, line 114)
- Modify: `frontend/app/brands/[id]/blogs/new/page.tsx` (checkbox + submit)

- [ ] **Step 1: Add `logo_url` to the profile type**

In `frontend/lib/types.ts`, in `interface BrandProfileContent`, after `visual_direction?: string | null;`:

```typescript
  logo_url?: string | null;
```

- [ ] **Step 2: Add the logo field to the profile editor**

In `frontend/components/brand/profile-editor.tsx`:

Extend `NULLABLE_STRING_FIELDS` (line 29):

```typescript
const NULLABLE_STRING_FIELDS = [
  "image_palette",
  "image_subject_hints",
  "visual_direction",
  "logo_url",
] as const;
```

Add the input after the "Visual direction" label (line 159):

```tsx
      <label>
        Logo URL
        <input
          type="url"
          defaultValue={profile.logo_url ?? ""}
          name="logo_url"
          placeholder="https://yourbrand.com/logo.png"
        />
      </label>
```

The existing `buildDiff` already handles nullable string fields, so no other editor change is needed. (Backend validates it as a URL via `HttpUrl`; `type="url"` gives client-side validation too.)

- [ ] **Step 3: Extend the API client**

In `frontend/lib/api.ts`, replace `createBlogJob` (line 114):

```typescript
export async function createBlogJob(
  brandId: string,
  keyword: string,
  includeImage: boolean = true,
): Promise<BlogJobOut> {
  return apiRequest<BlogJobOut>(`/v1/brands/${brandId}/blogs`, {
    method: "POST",
    body: { keyword, include_image: includeImage },
  });
}
```

- [ ] **Step 4: Add the checkbox to the new-blog form**

In `frontend/app/brands/[id]/blogs/new/page.tsx`:

Add state next to the existing `keyword` state (line 24):

```typescript
  const [includeImage, setIncludeImage] = useState(true);
```

Pass it on submit — in `handleSubmit`, change:

```typescript
      const job = await createBlogJob(brandId, keyword.trim());
```

to:

```typescript
      const job = await createBlogJob(brandId, keyword.trim(), includeImage);
```

Add the checkbox between the keyword `<label>` and the error paragraph in the form:

```tsx
            <label style={{ flexDirection: "row", alignItems: "center", gap: 10, fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={includeImage}
                onChange={(e) => setIncludeImage(e.target.checked)}
                style={{ width: "auto", height: "auto", accentColor: "var(--accent)" }}
              />
              Generate a featured image
            </label>
            {includeImage && (
              <p className="meta" style={{ margin: "-8px 0 0 26px", fontSize: "0.78rem" }}>
                If your brand has a logo set in Brand DNA, it will be stamped on the image.
              </p>
            )}
```

(The global `label` style is `flex-direction: column`, so the inline row override is required for a checkbox row.)

- [ ] **Step 5: Typecheck the frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: no output (clean).

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/types.ts frontend/components/brand/profile-editor.tsx frontend/lib/api.ts "frontend/app/brands/[id]/blogs/new/page.tsx"
git commit -m "feat: featured-image opt-in on blog creation and brand logo URL field"
```

---

### Task 7: End-to-end smoke check (manual, dev stack)

No code changes — verifies the wiring against the real stack.

- [ ] **Step 1: Start the stack**

Run: `docker compose up -d minio postgres redis` (plus backend/worker/frontend however you normally run them — `docker compose up -d` or local uvicorn + `npm run dev`). If running the backend locally (not in compose), export the MinIO env first:

```bash
export S3_ENDPOINT_URL=http://localhost:9000 S3_ACCESS_KEY=100xai-dev S3_SECRET_KEY=100xai-dev-secret S3_PUBLIC_URL=http://localhost:9000
```

- [ ] **Step 2: Set a logo on a brand**

In the UI: Brand → DNA → Logo URL → paste any reachable PNG (e.g. the brand's real logo) → Save profile. (Only editable while the brand is in PENDING_REVIEW / profile unlocked; for an already-locked brand, set it directly in SQL: `UPDATE brand_profiles SET logo_url='https://.../logo.png' WHERE brand_id='...';`)

- [ ] **Step 3: Generate a blog with the image option on**

UI: Brand → Blogs → New Article → keyword → leave "Generate a featured image" checked → Generate. Wait for `PENDING_REVIEW`.

Verify: the review page hero image shows the logo stamped bottom-right, and `blog_drafts.featured_image_url` points at `http://localhost:9000/100xai-uploads/branded/<job-id>-featured.jpg`.

- [ ] **Step 4: Generate a blog with the image option off**

Same flow with the checkbox unticked. Verify the worker log prints `Image generation skipped — include_image=False on this job` and the draft has `featured_image_url IS NULL` (review page renders without a hero, which the blog-preview layout already handles).

---

## Out of scope (deliberately)

- **Logo file upload** — the logo is referenced by URL (brands almost always have a hosted logo; `HttpUrl` validation applies). A proper upload endpoint can reuse `storage.upload_public_image` later.
- **Auto-extracting the logo during the brand crawl** — nice future enhancement for `extractor.py`, not needed for the feature to work.
- **Placid template changes** — when `placid_template_id` is configured the Placid composite still runs first; the Pillow logo stamp is applied on top of whatever Placid returns, so both paths get the logo.
- **Replacing the `store_image_in_bucket` stub** — it still passes URLs through unchanged; the branded image is already hosted by the time it reaches that call.
