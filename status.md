# 100xAI Code Status

Updated: 2026-05-28

## Current Implementation Status

The repo has moved from a scaffold into the first onboarding foundation slice. It is not the full product yet. The implemented work covers the backend structure, onboarding data model, basic authenticated brand/profile APIs, worker placeholders, frontend route skeleton, and prompt/integration boundaries.

## Implemented

### Repo Structure

The codebase now follows the authoritative layout from `AGENTS.md`:

```text
backend/     FastAPI backend, SQLAlchemy models, schemas, routers, services, migrations
worker/      RQ worker entrypoint and onboarding task targets
frontend/    Next.js admin panel skeleton
packages/    shared schemas and prompt ownership folders
docs/        architecture/spec notes
```

The older `apps/api`, `apps/web`, and `apps/worker` scaffold was removed to avoid two competing app layouts.

### Backend

Implemented under `backend/app/`:

- FastAPI app entrypoint: `backend/app/main.py`
- Runtime config: `backend/app/config.py`
- DB session setup: `backend/app/db.py`
- JWT helper and bearer-token dependency:
  - `backend/app/auth/jwt.py`
  - `backend/app/deps.py`
- RBAC helper: `backend/app/auth/rbac.py`
- Tenant-scoped brand repository: `backend/app/repositories/brands.py`
- Onboarding business logic: `backend/app/services/brand_service.py`
- Manual profile source materialization: `backend/app/services/manual_sources.py`
- Audit writer: `backend/app/services/audit.py`
- Fernet credential encryption: `backend/app/services/encryption.py`

### Data Model

SQLAlchemy models exist for:

- `organizations`
- `users`
- `brands`
- `brand_profiles`
- `brand_knowledge_sources`
- `brand_knowledge_chunks`
- `integration_accounts`
- `integration_tokens`
- `jobs`
- `audit_logs`

Files:

- `backend/app/models/core.py`
- `backend/app/models/onboarding.py`

An Alembic migration was added:

- `backend/alembic/versions/20260527_0001_onboarding_subsystem.py`

### API Endpoints

Implemented routes:

```text
GET    /health
GET    /v1/ready
POST   /v1/brands
GET    /v1/brands
GET    /v1/brands/{brand_id}
DELETE /v1/brands/{brand_id}
POST   /v1/brands/{brand_id}/profile
GET    /v1/brands/{brand_id}/profile
PATCH  /v1/brands/{brand_id}/profile
POST   /v1/brands/{brand_id}/approve
GET    /v1/jobs/{job_id}
```

Current behavior:

- `POST /v1/brands` supports `dna_source = crawl` and `dna_source = manual`.
- Crawl-path brand creation creates a `brand.onboard` job row and marks the brand `CRAWLING`.
- Manual-path brand creation creates the brand in `DRAFT` without an onboarding job.
- Manual profile submission creates a `brand_profiles` row and materializes key manual fields into knowledge sources.
- Brand profile patching is allowed only during `PENDING_REVIEW`.
- Approval is admin-only, locks the profile, and moves the brand to `READY`.
- Brand listing is tenant-scoped by `org_id` from the JWT.

### Brand DNA Schema

Backend schema files:

- `backend/app/schemas/brand_profile.py`
- `backend/app/schemas/brand_profile_v1.json`

Shared schema package:

- `packages/shared-schemas/brand-dna/schema.json`

Note: the backend schema follows `ONBOARDING_FOUNDATION.md` field names such as `audience_personas`, `ctas`, and `tone_rules`.

### Integrations

Integration boundary added under `backend/app/integrations/`:

- base provider interface
- provider registry
- WordPress provider
- Shopify/Webflow/custom provider stubs

Current WordPress support is a provider class boundary, not a complete API route yet.

### Prompts

Backend Brand DNA prompt version added:

```text
backend/prompts/brand_dna/v1/
  extraction.txt
  retry.txt
  system_notes.md
```

General prompt ownership folders still exist under `packages/prompts/` for the no-code/prompt owner.

### Worker

Worker files:

- `worker/main.py`
- `worker/tasks/onboarding.py`
- `worker/tasks/ingest.py`
- `worker/tasks/purge.py`

The worker has stable RQ entrypoints. The crawl/extract/ingest stages live in `backend/app/services/{crawler,extractor,ingestion}.py` and are orchestrated by `services/onboarding_pipeline.py` on a single asyncio loop, with idempotent re-crawl on retry and per-stage status persistence. Module-level engine + sessionmaker are shared across tasks.

### Frontend

Frontend skeleton added under `frontend/`:

- root layout
- home page
- brands page
- create-brand page
- basic `CreateBrandForm`
- shared frontend types

The frontend talks to the backend through a same-origin `/api/[...path]` route handler that proxies to `BACKEND_URL` and injects the server-only `API_TOKEN` — no token reaches the browser bundle. Demo/mock pages render only when `NEXT_PUBLIC_DEMO_MODE=true`. Active-job panels poll `/v1/jobs/:id` every 3s while `QUEUED`/`RUNNING`.

## Current Architecture

```text
Frontend: Next.js admin panel
    |
    | JSON over HTTP
    v
Backend: FastAPI
    |
    | SQLAlchemy
    v
Postgres: operational source of truth

Backend also writes:
    - jobs for async work
    - audit_logs for important actions

Worker: RQ process
    |
    | future crawl/extract/ingest jobs
    v
External systems:
    - OpenRouter for Brand DNA extraction
    - OpenAI embeddings
    - Pinecone vector storage
    - S3-compatible storage
    - WordPress publishing
```

Important boundary rule:

- FastAPI routes validate input, enforce auth/tenant scope, persist data, and create jobs.
- Long-running work belongs in `worker/`.
- Provider-specific code belongs in `backend/app/integrations/`.
- Business rules belong in `backend/app/services/`.
- Tenant-scoped DB reads belong in `backend/app/repositories/`.

## Tests Added

Tests live under `backend/tests/`.

Current coverage:

- Brand profile schema validation
- Credential encryption round-trip
- Crawl-path brand creation creates a job
- Manual-path brand creation does not create an onboarding job
- Brand listing is tenant-scoped
- Manual profile submit and approval flow
- Locked profile rejects later edits

Verification command:

```bash
PYTHONPATH=backend python -m pytest -p no:rerunfailures backend/tests -q
```

Last known result:

```text
8 passed
```

## Not Implemented Yet

The following are still pending:

- real login endpoint and password hashing
- S3/MinIO upload/presigned URL endpoint
- generation pipeline (brief → outline → article)
- LinkedIn (Unipile) and WhatsApp (VAPI) distribution
- CMS publishing adapters beyond WordPress
- operational dashboard and content calendar
- WordPress integration API route
- hard-delete cleanup for Pinecone/S3/integration revocation
- full admin UI forms, tabs, polling, and auth
- frontend API client wiring
- real Docker app containers
- production-grade migrations tested against Postgres

## Next Recommended Task

Implement the queue-backed onboarding job boundary:

1. Add RQ dependency wiring in the backend.
2. Make `POST /v1/brands` enqueue `worker.tasks.onboarding.run_onboarding_pipeline`.
3. Add tests that verify crawl-path creation enqueues a job while manual path does not.
4. Keep the worker task implementation as a placeholder until crawler work starts.

