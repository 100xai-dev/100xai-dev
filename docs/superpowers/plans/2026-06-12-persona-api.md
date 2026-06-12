# Brand Persona API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the brand persona (the 10 onboarding fields) in the backend and serve it to the new frontend's `/persona` and `/onboarding` pages, replacing the current `localStorage`-only prototype.

**Architecture:** A new `brand_personas` table holds one persona row per brand (1:1, FK to `brands`). Two endpoints under `/v1/brands/{brand_id}/persona` — `GET` (read) and `PUT` (upsert) — expose it, following the exact auth/ownership pattern of the existing brand routers. The persona's *derived* presentation (palette, voice cards, beliefs, values) stays computed client-side in `buildPersona()` — the backend only stores the raw inputs. The frontend scheduler context loads/saves the persona against the API (scoped to the user's current brand) instead of `localStorage`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Alembic, Postgres (db `100xai`), pytest with the in-memory-SQLite `conftest.py` fixtures (backend); Next.js 14 + TypeScript (frontend).

---

## Context an implementer needs

**Why this exists:** The new frontend at `/Users/shubhamrathod/Downloads/100x-tool-frontend` has a persona feature (`app/onboarding/page.tsx` → `app/persona/page.tsx`) that is a client-only prototype. It collects 10 fields into React context, persists them to `localStorage["schedulr.brand"]`, and derives the whole persona document client-side via `buildPersona()` in `lib/scheduler/persona.ts`. There is **no backend** for it. This plan adds that backend and wires the two pages to it. The blog/DNA/pipeline/SERP/scheduling features the product also needs are **already** served by the backend and are explicitly out of scope here (see end).

**The 10 persona fields** (frontend `BrandData` shape in `lib/scheduler/persona.ts`):
`name`, `domain`, `url`, `one` (one-liner), `aud` (audience), `tone` (string[] of voice tags), `founder`, `role`, `mission`, `accent` (hex color).

**Design decisions (made deliberately):**
- **New `brand_personas` table, not an extension of `BrandProfile`.** `BrandProfile` feeds the blog-generation LLM prompts (tone_rules, banned_phrases, audience_personas, etc.); coupling the presentation-oriented persona fields to it would have a large blast radius on the content pipeline. The persona is a distinct artifact. Some fields (name, url, one-liner, audience) duplicate brand data — acceptable; a future sync task can reconcile if needed (YAGNI now).
- **Per-brand, 1:1.** The production backend is multi-brand (org → many brands). Persona is scoped to a brand at `/v1/brands/{brand_id}/persona`. The prototype's single global brand maps to "the current brand" in the frontend (Task 6 resolves it).
- **Backend field names are clean** (`one_liner`, `audience`, `tone_tags`, `founder_name`, `founder_role`, `accent_color`); the frontend maps `BrandData`↔`Persona` in `lib/api.ts` (Task 6).
- **`PUT` is an upsert** — onboarding may save repeatedly; there is exactly one persona per brand.

**Backend conventions (verified in this repo):**
- Routers live in `backend/app/routers/`, mounted in `backend/app/main.py` with `app.include_router(<router>, prefix="/v1")`. A router declares its own sub-prefix without `/v1` (e.g. `APIRouter(prefix="/brands/{brand_id}/sources")`), and the endpoint at the prefix root uses path `""`.
- Auth imports: `from app.auth.rbac import require_role`, `from app.deps import CurrentUser, get_current_user`, `from app.db import get_db`.
- Brand ownership: `from app.repositories.brands import get_brand` — `get_brand(db, brand_id, org_id) -> Brand | None`.
- `from app.models.base import Base, TimestampMixin, uuid_str` — `TimestampMixin` supplies `created_at`/`updated_at`; `uuid_str` is the id default.
- Models must be imported in `backend/app/models/__init__.py` (and added to `__all__`) so `Base.metadata` includes them — the test DB is built from metadata via `Base.metadata.create_all`.
- Latest alembic revision is `20260612_0012` (`backend/alembic/versions/20260612_0012_brand_profile_logo_url.py`).
- Tests: `cd backend && venv/bin/python -m pytest tests/<file> -v`. Fixtures in `backend/tests/conftest.py`: `client` (TestClient + in-memory sqlite), `db_session`, `create_user(session, email, role="admin")`, `auth_headers(user)`.
- **Known pre-existing failure** (leave alone): `test_content_brief_coerces_list_audience_and_range_word_count`.

**Repo state:** branch `feat/email-verification-razorpay-terms`. Commit ONLY the files listed in each task; do not sweep in unrelated working-tree changes.

---

### Task 1: `BrandPersona` model + registration

**Files:**
- Create: `backend/app/models/persona.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_persona.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_persona.py`:

```python
"""Tests for the brand persona model and API."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.onboarding import Brand
from app.models.persona import BrandPersona
from tests.conftest import auth_headers, create_user


def _brand(db: Session, user) -> Brand:
    brand = Brand(
        org_id=user.org_id,
        name="Acme",
        website_url="https://acme.example",
        dna_source="crawl",
        status="READY",
        created_by=user.id,
    )
    db.add(brand)
    db.commit()
    return brand


def test_brand_persona_model_persists(db_session: Session) -> None:
    user = create_user(db_session, "persona-model@example.com")
    brand = _brand(db_session, user)

    persona = BrandPersona(
        brand_id=brand.id,
        name="Acme",
        domain="acme.example",
        url="https://acme.example",
        one_liner="We make robots.",
        audience="Warehouse operators",
        tone_tags=["Bold", "Warm"],
        founder_name="Ada Lovelace",
        founder_role="Founder & CEO",
        mission="Zero downtime warehouses",
        accent_color="#F58000",
    )
    db_session.add(persona)
    db_session.commit()

    fetched = db_session.query(BrandPersona).filter(
        BrandPersona.brand_id == brand.id
    ).first()
    assert fetched is not None
    assert fetched.tone_tags == ["Bold", "Warm"]
    assert fetched.accent_color == "#F58000"
    assert fetched.created_at is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && venv/bin/python -m pytest tests/test_persona.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.persona'`.

- [ ] **Step 3: Create the model**

Create `backend/app/models/persona.py`:

```python
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_str


class BrandPersona(Base, TimestampMixin):
    """One brand-persona record per brand (1:1).

    Stores the raw onboarding inputs only; the presentation persona
    (palette, voice cards, beliefs, values) is derived client-side.
    """

    __tablename__ = "brand_personas"

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=uuid_str)
    brand_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    one_liner: Mapped[str] = mapped_column(Text, nullable=False, default="")
    audience: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tone_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    founder_name: Mapped[str | None] = mapped_column(String)
    founder_role: Mapped[str | None] = mapped_column(String)
    mission: Mapped[str | None] = mapped_column(Text)
    accent_color: Mapped[str | None] = mapped_column(String)
```

- [ ] **Step 4: Register the model**

In `backend/app/models/__init__.py`, add an import line next to the other model imports:

```python
from app.models.persona import BrandPersona
```

and add `"BrandPersona",` to the `__all__` list.

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && venv/bin/python -m pytest tests/test_persona.py -v`
Expected: `test_brand_persona_model_persists PASSED` (the sqlite test DB is built from `Base.metadata`, so the model + registration is enough).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/persona.py backend/app/models/__init__.py backend/tests/test_persona.py
git commit -m "feat: add BrandPersona model

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Persona schemas + alembic migration

**Files:**
- Create: `backend/app/schemas/persona.py`
- Create: `backend/alembic/versions/20260612_0013_brand_personas.py`

- [ ] **Step 1: Create the schemas**

Create `backend/app/schemas/persona.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonaContent(BaseModel):
    """Persona input — the raw onboarding fields."""

    name: str = Field(..., min_length=1, max_length=200)
    domain: str | None = None
    url: str | None = None
    one_liner: str = ""
    audience: str = ""
    tone_tags: list[str] = Field(default_factory=list)
    founder_name: str | None = None
    founder_role: str | None = None
    mission: str | None = None
    accent_color: str | None = None


class PersonaOut(PersonaContent):
    id: str
    brand_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

Note: `url` is a plain `str | None`, not `HttpUrl` — the onboarding form stores `"https://" + domain` where domain may be partial; lenient typing avoids spurious 422s. `accent_color` is a hex string.

- [ ] **Step 2: Create the migration**

Create `backend/alembic/versions/20260612_0013_brand_personas.py`:

```python
"""Add brand_personas table

Revision ID: 20260612_0013
Revises: 20260612_0012
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "20260612_0013"
down_revision = "20260612_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_personas",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column(
            "brand_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("one_liner", sa.Text(), nullable=False, server_default=""),
        sa.Column("audience", sa.Text(), nullable=False, server_default=""),
        sa.Column("tone_tags", sa.JSON(), nullable=True),
        sa.Column("founder_name", sa.String(), nullable=True),
        sa.Column("founder_role", sa.String(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("accent_color", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("brand_personas")
```

Note (verified): `TimestampMixin` in `backend/app/models/base.py` declares `created_at`/`updated_at` as `DateTime(timezone=True)` with **Python-side** defaults (`default=utcnow`, `updated_at` also `onupdate=utcnow`) — no DB server default. On this brand-new table the migration's `server_default=sa.func.now()` is harmless and keeps the NOT NULL columns safe for any non-ORM insert; the ORM always sets both via the mixin. The column definitions above are correct as written.

- [ ] **Step 3: Apply the migration to the dev database**

Run: `cd backend && venv/bin/alembic upgrade head`
Expected: `Running upgrade 20260612_0012 -> 20260612_0013`.

- [ ] **Step 4: Verify the migration is reversible**

Run: `cd backend && venv/bin/alembic downgrade -1 && venv/bin/alembic upgrade head`
Expected: clean down then up, no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/persona.py backend/alembic/versions/20260612_0013_brand_personas.py
git commit -m "feat: add persona schemas and brand_personas migration

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Persona router (GET + PUT upsert) + registration

**Files:**
- Create: `backend/app/routers/persona.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_persona.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_persona.py`:

```python
def test_get_persona_404_when_absent(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "persona-get-404@example.com")
    brand = _brand(db_session, user)

    resp = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user))
    assert resp.status_code == 404


def test_put_persona_creates_then_get_returns_it(
    client: TestClient, db_session: Session
) -> None:
    user = create_user(db_session, "persona-put@example.com")
    brand = _brand(db_session, user)

    body = {
        "name": "Acme",
        "domain": "acme.example",
        "url": "https://acme.example",
        "one_liner": "We make robots.",
        "audience": "Warehouse operators",
        "tone_tags": ["Bold", "Warm"],
        "founder_name": "Ada Lovelace",
        "founder_role": "Founder & CEO",
        "mission": "Zero downtime warehouses",
        "accent_color": "#F58000",
    }
    put = client.put(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user), json=body)
    assert put.status_code == 200
    assert put.json()["tone_tags"] == ["Bold", "Warm"]
    assert put.json()["brand_id"] == brand.id

    got = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(user))
    assert got.status_code == 200
    assert got.json()["founder_name"] == "Ada Lovelace"
    assert got.json()["one_liner"] == "We make robots."


def test_put_persona_upserts_in_place(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, "persona-upsert@example.com")
    brand = _brand(db_session, user)

    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(user),
        json={"name": "Acme", "one_liner": "v1", "tone_tags": ["Bold"]},
    )
    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(user),
        json={"name": "Acme", "one_liner": "v2", "tone_tags": ["Warm", "Playful"]},
    )

    personas = db_session.query(BrandPersona).filter(
        BrandPersona.brand_id == brand.id
    ).all()
    assert len(personas) == 1
    assert personas[0].one_liner == "v2"
    assert personas[0].tone_tags == ["Warm", "Playful"]


def test_persona_scoped_to_org(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, "persona-owner@example.com")
    brand = _brand(db_session, owner)
    client.put(
        f"/v1/brands/{brand.id}/persona",
        headers=auth_headers(owner),
        json={"name": "Acme"},
    )

    outsider = create_user(db_session, "persona-outsider@example.com")
    # Outsider is in a different org → must not see the brand or its persona.
    resp = client.get(f"/v1/brands/{brand.id}/persona", headers=auth_headers(outsider))
    assert resp.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && venv/bin/python -m pytest tests/test_persona.py -v`
Expected: the four API tests FAIL with 404/405 (route not registered yet).

- [ ] **Step 3: Create the router**

Create `backend/app/routers/persona.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.rbac import require_role
from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.persona import BrandPersona
from app.repositories.brands import get_brand
from app.schemas.persona import PersonaContent, PersonaOut

router = APIRouter(prefix="/brands/{brand_id}/persona", tags=["persona"])


def _require_brand(db: Session, brand_id: str, org_id: str):
    brand = get_brand(db, brand_id, org_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="brand not found")
    return brand


@router.get("", response_model=PersonaOut)
def get_persona(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PersonaOut:
    _require_brand(db, brand_id, current_user.org_id)
    persona = db.query(BrandPersona).filter(BrandPersona.brand_id == brand_id).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="persona not found")
    return PersonaOut.model_validate(persona)


@router.put("", response_model=PersonaOut)
def upsert_persona(
    brand_id: str,
    payload: PersonaContent,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PersonaOut:
    require_role(current_user.role, {"admin", "team_member"})
    _require_brand(db, brand_id, current_user.org_id)

    persona = db.query(BrandPersona).filter(BrandPersona.brand_id == brand_id).first()
    data = payload.model_dump()
    if persona:
        for key, value in data.items():
            setattr(persona, key, value)
    else:
        persona = BrandPersona(brand_id=brand_id, **data)
        db.add(persona)
    db.commit()
    db.refresh(persona)
    return PersonaOut.model_validate(persona)
```

- [ ] **Step 4: Register the router**

In `backend/app/main.py`:

Add the import next to the other router imports:

```python
from app.routers.persona import router as persona_router
```

Add the registration next to the other `app.include_router(..., prefix="/v1")` lines:

```python
app.include_router(persona_router, prefix="/v1")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && venv/bin/python -m pytest tests/test_persona.py -v`
Expected: all persona tests PASS (model test + the four API tests).

- [ ] **Step 6: Run the full suite for regressions**

Run: `cd backend && venv/bin/python -m pytest tests/ -q`
Expected: all pass except the known pre-existing `test_content_brief_coerces_list_audience_and_range_word_count`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/persona.py backend/app/main.py backend/tests/test_persona.py
git commit -m "feat: add brand persona GET/PUT endpoints

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Frontend wiring (in `/Users/shubhamrathod/Downloads/100x-tool-frontend`)

> **Prerequisite — merge conflicts.** `lib/api.ts` and `lib/types.ts` (among others) currently contain unresolved Git conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) and `lib/api.ts` has a duplicate `startSerpAnalysis`. The app will not compile until these are resolved. Resolve the conflicts in `lib/api.ts` and `lib/types.ts` **before** Task 4 (keep both upstream and feature additions; dedupe `startSerpAnalysis`). Verify with `cd /Users/shubhamrathod/Downloads/100x-tool-frontend && npx tsc --noEmit` producing no output before proceeding. If the conflicts are non-trivial, STOP and surface them rather than guessing.

Frontend env: `lib/config.ts` exposes `getBackendBaseUrl()`, `isDemoMode()` (`NEXT_PUBLIC_DEMO_MODE === "true"`), and the proxy at `app/api/[...path]/route.ts` injects the bearer token server-side. Client components call same-origin `/api/v1/...`.

### Task 4: Persona types + API client mapping

**Files:**
- Modify: `lib/types.ts`
- Modify: `lib/api.ts`

- [ ] **Step 1: Add the Persona type**

In `lib/types.ts` (after resolving conflicts), add:

```typescript
export interface Persona {
  id: string;
  brand_id: string;
  name: string;
  domain: string | null;
  url: string | null;
  one_liner: string;
  audience: string;
  tone_tags: string[];
  founder_name: string | null;
  founder_role: string | null;
  mission: string | null;
  accent_color: string | null;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 2: Add the API client functions with BrandData mapping**

In `lib/api.ts`, add (importing `BrandData` from `@/lib/scheduler/persona` and `Persona` from `@/lib/types`):

```typescript
import type { BrandData } from "@/lib/scheduler/persona";
import type { Persona } from "@/lib/types";

// BrandData (frontend) <-> Persona (backend) field mapping.
export function personaToBrandData(p: Persona): BrandData {
  return {
    name: p.name,
    domain: p.domain ?? "",
    url: p.url ?? "",
    one: p.one_liner,
    aud: p.audience,
    tone: p.tone_tags ?? [],
    founder: p.founder_name ?? "",
    role: p.founder_role ?? "",
    mission: p.mission ?? "",
    accent: p.accent_color ?? "#F58000",
  };
}

function brandDataToPayload(d: BrandData) {
  return {
    name: d.name,
    domain: d.domain || null,
    url: d.url || null,
    one_liner: d.one,
    audience: d.aud,
    tone_tags: d.tone,
    founder_name: d.founder || null,
    founder_role: d.role || null,
    mission: d.mission || null,
    accent_color: d.accent || null,
  };
}

export async function getPersona(brandId: string): Promise<Persona | null> {
  try {
    return await apiRequest<Persona>(`/v1/brands/${brandId}/persona`);
  } catch {
    return null; // 404 = not composed yet
  }
}

export async function savePersona(brandId: string, data: BrandData): Promise<Persona> {
  return apiRequest<Persona>(`/v1/brands/${brandId}/persona`, {
    method: "PUT",
    body: brandDataToPayload(data),
  });
}
```

Match `apiRequest`'s actual signature/options shape (read the resolved `lib/api.ts` — e.g. it may take `{ method, body }`). Adjust the calls to fit.

- [ ] **Step 3: Typecheck**

Run: `cd /Users/shubhamrathod/Downloads/100x-tool-frontend && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add lib/types.ts lib/api.ts
git commit -m "feat: persona API client and BrandData mapping

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 5: Scoped brand id + persona hydration in the scheduler context

The prototype keeps one global `brand` in context, hydrated from `localStorage`. To use the backend, the context needs to know **which brand** the persona belongs to. Resolve a `brandId` (the user's most-recent brand) and hydrate `brand` from `getPersona(brandId)`; fall back to `localStorage`/`DEFAULT_BRAND` in demo mode or when no brand/persona exists.

**Files:**
- Modify: `lib/scheduler/context.tsx`

- [ ] **Step 1: Add brandId resolution + persona hydration**

In `lib/scheduler/context.tsx`:
- Add `brandId: string | null` to the context value and a `useState<string | null>(null)` for it.
- On mount (when `!isDemoMode()`), resolve the current brand: call `listBrands()` and take the first item's `id` (most-recent; `listBrands` already sorts desc). Persist it to `localStorage["schedulr.brandId"]` and read it back on subsequent mounts. If the user has no brands, leave `brandId` null and keep the existing `localStorage`/`DEFAULT_BRAND` behavior.
- After `brandId` resolves, call `getPersona(brandId)`; if it returns a persona, `setBrandState(personaToBrandData(persona))`; otherwise keep the current default.
- Keep the existing `localStorage["schedulr.brand"]` hydration as the demo-mode / no-backend fallback.

Concrete shape (adapt to the existing context code):

```typescript
const BRAND_ID_KEY = "schedulr.brandId";

// inside the provider:
const [brandId, setBrandId] = useState<string | null>(null);

useEffect(() => {
  if (isDemoMode()) return; // demo: keep localStorage hydration below
  let cancelled = false;
  (async () => {
    let id = localStorage.getItem(BRAND_ID_KEY);
    if (!id) {
      const brands = await listBrands().catch(() => null);
      id = brands?.items?.[0]?.id ?? null;
      if (id) localStorage.setItem(BRAND_ID_KEY, id);
    }
    if (cancelled || !id) return;
    setBrandId(id);
    const persona = await getPersona(id);
    if (!cancelled && persona) setBrandState(personaToBrandData(persona));
  })();
  return () => { cancelled = true; };
}, []);
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/shubhamrathod/Downloads/100x-tool-frontend && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add lib/scheduler/context.tsx
git commit -m "feat: hydrate brand persona from backend in scheduler context

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 6: Onboarding saves to the backend

**Files:**
- Modify: `app/onboarding/page.tsx`

- [ ] **Step 1: Persist on generate**

In `app/onboarding/page.tsx`, `generate()` currently calls `setBrand(data)` (which writes `localStorage`) then runs the progress animation and routes to `/persona`. Change it so that, when not in demo mode and a `brandId` is available from context, it also persists to the backend before routing:

- Pull `brandId` (and `setBrand`) from `useScheduler()`.
- After building `data`, call `setBrand(data)` (keep — updates context + localStorage immediately for snappy UX), then:

```typescript
if (!isDemoMode() && brandId) {
  try {
    await savePersona(brandId, data);
  } catch {
    // non-fatal: context/localStorage already holds it; surface a toast if desired
  }
}
```

- The existing 5-step animation and `router.push("/persona")` stay. Make `generate` `async` (the timer logic can remain; just `await savePersona` before starting the animation, or fire it and let the animation cover the latency — prefer awaiting so `/persona` reads fresh server state).
- If `brandId` is null (user has no brand yet), keep the current localStorage-only behavior — do not block onboarding. (Creating a brand from onboarding is out of scope; see follow-ups.)

- [ ] **Step 2: Typecheck**

Run: `cd /Users/shubhamrathod/Downloads/100x-tool-frontend && npx tsc --noEmit`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add "app/onboarding/page.tsx"
git commit -m "feat: persist persona to backend on onboarding

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

### Task 7: Manual end-to-end verification

No code — verifies the wiring against the running stack.

- [ ] **Step 1:** Ensure the backend is running with the migration applied (`cd backend && venv/bin/alembic current` shows `20260612_0013`) and the frontend env points `BACKEND_URL` at it with a valid `API_TOKEN`. Set `NEXT_PUBLIC_DEMO_MODE=false`.
- [ ] **Step 2:** With at least one brand existing for the token's org, open `/onboarding`, fill the fields, click **Generate brand persona**. Confirm a `PUT /v1/brands/{id}/persona` succeeds (network tab) and `/persona` renders the entered data.
- [ ] **Step 3:** Reload `/persona` in a fresh tab (clears nothing) — it should render from the backend (`GET /v1/brands/{id}/persona`), proving persistence survives a `localStorage` clear. Optionally clear `localStorage` and reload to confirm.
- [ ] **Step 4:** Confirm `DELETE /v1/brands/{id}` cascades (persona row removed) — `SELECT * FROM brand_personas WHERE brand_id=...` returns nothing after deleting the brand.

---

## Out of scope (separate plans / follow-ups)

- **Resolving ALL frontend merge conflicts** (`app/layout.tsx`, `app/globals.css`, `app/brands/[id]/page.tsx`, `app/brands/[id]/integrations/wordpress/page.tsx`) and turning off `DEMO_MODE` so the already-backed `/brands/*` pages (DNA, jobs, keywords, SERP, blogs, sources, integrations, blog-schedule, billing) render live data. These endpoints already exist; this is integration/verification work, not new APIs — worth its own plan.
- **Blog publishing beyond WordPress.** The blog `approve-article` path (`backend/app/routers/blogs.py` → `_publish_to_wordpress`) currently publishes only to WordPress, although integrations + the publishing layer support Shopify/Webflow/Ghost/webhook. Wiring `approve-article` to publish via the brand's configured channel (Shopify, Webflow, "custom website"/webhook) is a separate backend task.
- **Auto-composing persona from the brand URL.** Onboarding's "Generate" is a manual form with a cosmetic progress animation. The backend already has a crawler + extractor for brand DNA (`dna_source="crawl"`); a future task could auto-populate persona fields from the site. Not needed for persistence to work.
- **The `/planner` social-post surface** (calendar of free-text multi-platform posts, dashboard aggregates, compose-modal AI, settings channel connections, analytics/queue placeholders) — explicitly deferred per product scope (blogs only, no social).

---

## Self-review notes

- Spec coverage: the 10 `BrandData` fields all map to `brand_personas` columns (name, domain, url, one→one_liner, aud→audience, tone→tone_tags, founder→founder_name, role→founder_role, mission, accent→accent_color). GET/PUT cover read + persist; upsert covers repeated onboarding saves.
- Type consistency: backend `PersonaContent`/`PersonaOut` field names are reused verbatim in the frontend `Persona` interface and the `brandDataToPayload`/`personaToBrandData` mappers.
- Open verification point flagged inline: confirm `TimestampMixin`'s column definitions when authoring the migration (Task 2 Step 2).
