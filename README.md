# 100xAI

AI marketing platform for onboarding brands, generating persistent Brand DNA, producing SEO/AEO blogs, publishing to CMS channels, and distributing approved content across LinkedIn and WhatsApp.

## Current Status

The onboarding foundation is partially implemented. This is not the full product yet; it covers the first backend slice from `ONBOARDING_FOUNDATION.md` plus structural alignment with `AGENTS.md`.

Completed so far:

- Authoritative `backend/`, `worker/`, and `frontend/` structure from `AGENTS.md`.
- FastAPI backend with health/readiness routes.
- PyJWT-based bearer-token dependency with `alg`/`iss`/`exp` validation and role checks.
- SQLAlchemy models for organizations, users, brands, profiles, knowledge sources/chunks, integrations, jobs, and audit logs.
- Alembic migrations for the onboarding subsystem, pending-delete state, and tenancy + indexes.
- Brand creation API for crawl/manual paths with Redis/RQ enqueue.
- Tenant-scoped brand listing and brand summary (single joined query, no N+1).
- Manual Brand DNA profile submission and PATCH editor that only sends dirty fields.
- Admin-only approval that locks the profile and marks the brand `READY`.
- Job status endpoint with org-scoped tenancy filter.
- Async crawler (`services/crawler.py`), LLM extractor with schema-validated retry, Pinecone ingestion.
- Onboarding pipeline orchestrator (`services/onboarding_pipeline.py`) with idempotent re-crawl, single shared event loop, and RQ retry for recoverable errors.
- WordPress integration provider boundary plus Shopify/Webflow/custom stubs.
- Fernet credential encryption service with multi-key keyring for rotation.
- RQ worker entrypoint with shared engine and stable task import targets.
- Next.js admin: brand list, create, detail, DNA review/editor, polling job status, manual profile form, hard-delete with audit trail. API token is server-only, proxied through `/api/*` route handler.
- Shared Brand DNA JSON schema embedded into the extraction prompt at render time.
- Docker Compose services for Postgres, Redis, and MinIO using real Dockerfiles under `infra/docker/`.

Verified so far:

- Backend tests pass with `PYTHONPATH=backend python -m pytest -p no:rerunfailures backend/tests -q`.
- JSON files validate with `python -m json.tool`.

Not done yet:

- Real login endpoint and password hashing.
- Source upload/presigned URL endpoint.
- Blog generation pipeline.
- LinkedIn / WhatsApp distribution.
- CMS publishing for non-WordPress adapters.
- Full operational dashboard and calendar views.

## Repo Layout

```text
backend/     FastAPI backend, models, schemas, routers, services, migrations
worker/      RQ worker entrypoints and onboarding task targets
frontend/    Next.js admin panel
packages/
  prompts/    versioned prompt contracts owned by content/prompt team
  shared-schemas/
infra/
  docker/     container definitions
  migrations/ database migrations
docs/
  architecture/
  specs/
scripts/      local development helpers
```

## Product Modules

The repo is organized around these future product domains:

- `auth`: users, roles, sessions, tenant scoping.
- `brands`: organizations, brands, onboarding state.
- `brand_dna`: structured brand memory and generation status.
- `knowledge_base`: source documents, chunks, embeddings, Pinecone metadata.
- `crawler`: website, sitemap, rendered-page, and SERP page extraction.
- `keywords`: seed keywords, expansion, scoring, and brand-fit filtering.
- `serp`: search results, competitor summaries, and retained metadata.
- `blog_jobs`: content pipeline from keyword to approved article.
- `images`: featured image prompt, generation, storage, and CMS attachment.
- `publishing`: CMS adapters and publish records.
- `linkedin`: posts, comments, DMs, approvals, Unipile calls, metrics.
- `whatsapp`: campaigns, recipients, consent gates, VAPI calls, tracked links.
- `dashboard`: operational status and summary metrics.
- `calendar`: scheduled content across blogs, LinkedIn, and WhatsApp.
- `audit`: immutable records for approval, send, publish, and token events.

## Ownership Split

Engineering owns:

- repo architecture
- frontend/backend implementation
- database models
- workers and queues
- crawler infrastructure
- Pinecone storage
- provider integrations
- publishing adapters
- approval workflows
- dashboard and calendar

Prompt/content owner owns files under `packages/prompts/`:

- Brand DNA extraction prompts
- fallback questions
- blog brief, outline, section, SEO/AEO, and final article prompts
- LinkedIn post/comment/DM prompts
- WhatsApp campaign copy prompts
- image generation prompts
- good and bad example outputs

Application code should load prompts from `packages/prompts/` instead of hard-coding prompt text.

## Running Locally (No Docker)

### Prerequisites

- Python 3.12
- Node.js 18+
- PostgreSQL (running locally)
- Redis — `brew install redis && brew services start redis` (Mac)

### 1. Clone and enter the repo

```bash
git clone <repo-url>
cd 100xai
```

### 2. Backend setup

```bash
cd backend
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
```

Create `backend/.env`:

```env
APP_ENV=development
APP_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg://<pg-user>:<pg-password>@localhost:5432/100xai
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=any-random-string-at-least-32-chars
JWT_EXPIRY_HOURS=24
OPENROUTER_API_KEY=sk-or-...
APIFY_API_KEY=apify_api_...
EXTRACTION_MODEL=anthropic/claude-3-5-sonnet-20241022
```

Create the database and run migrations:

```bash
createdb 100xai
venv/bin/alembic upgrade head
```

Seed a dev org and user (one-time):

```bash
venv/bin/python -c "
from app.db import SessionLocal
from app.models.core import Organization, User
db = SessionLocal()
org_id = '00000000-0000-0000-0000-000000000001'
user_id = '00000000-0000-0000-0000-000000000001'
if not db.get(Organization, org_id):
    db.add(Organization(id=org_id, name='Dev Org'))
if not db.get(User, user_id):
    db.add(User(id=user_id, org_id=org_id, email='dev@100xai.com', password_hash='dev', name='Dev Admin', role='admin'))
db.commit()
print('Seeded')
db.close()
"
```

Generate a dev API token:

```bash
venv/bin/python -c "
from app.auth.jwt import create_access_token
print(create_access_token(user_id='00000000-0000-0000-0000-000000000001', org_id='00000000-0000-0000-0000-000000000001', role='admin'))
"
```

Start the backend (run from `backend/` directory):

```bash
venv/bin/uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
BACKEND_URL=http://localhost:8000
API_TOKEN=<token from step above>
```

Start the frontend:

```bash
npm run dev
```

Open `http://localhost:3000`.

### 4. Worker setup (for crawl-path brand onboarding)

Run from the repo root:

```bash
cd /path/to/100xai
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
PYTHONPATH=backend:. \
OPENROUTER_API_KEY=sk-or-... \
APIFY_API_KEY=apify_api_... \
DATABASE_URL=postgresql+psycopg://<pg-user>:<pg-password>@localhost:5432/100xai \
REDIS_URL=redis://localhost:6379/0 \
JWT_SECRET=any-random-string-at-least-32-chars \
EXTRACTION_MODEL=anthropic/claude-3-5-sonnet-20241022 \
backend/venv/bin/rq worker --with-scheduler onboarding purge default
```

> `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` is required on macOS only.

### Required API Keys

| Key | Purpose | Get it at |
|---|---|---|
| `OPENROUTER_API_KEY` | LLM brand DNA extraction | openrouter.ai |
| `APIFY_API_KEY` | Website crawling | apify.com |

Pinecone and OpenAI keys are optional — vector ingestion is skipped if not set.

## Next Engineering Slice

1. Real `/v1/auth/login` with password hashing and refresh.
2. Source upload + presigned URL endpoint and S3/MinIO ingestion path.
3. Blog brief → outline → section → article generation pipeline.
4. CMS publishing adapters beyond WordPress (Shopify, Webflow, custom).
5. LinkedIn (Unipile) and WhatsApp (VAPI) distribution.
6. Operational dashboard and content calendar.

## Important Files

- `backend/app/main.py`: FastAPI app.
- `backend/app/routers/brands.py`: onboarding brand/profile endpoints.
- `backend/app/models/`: SQLAlchemy onboarding models.
- `backend/app/services/brand_service.py`: onboarding business rules.
- `backend/app/integrations/`: provider interfaces and WordPress/stub adapters.
- `worker/main.py`: RQ worker entrypoint.
- `frontend/app/brands/new/page.tsx`: current brand creation page.
- `packages/shared-schemas/brand-dna/schema.json`: Brand DNA contract.
- `packages/prompts/`: prompt files owned by the prompt/content workflow.
- `backend/prompts/brand_dna/v1/`: backend-loaded Brand DNA prompt version.
- `docs/architecture/domain-boundaries.md`: domain boundary reference.
- `docs/architecture/repo-architecture.md`: repo architecture reference.
