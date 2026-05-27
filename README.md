# 100xAI

AI marketing platform for onboarding brands, generating persistent Brand DNA, producing SEO/AEO blogs, publishing to CMS channels, and distributing approved content across LinkedIn and WhatsApp.

## Current Status

The onboarding foundation is partially implemented. This is not the full product yet; it covers the first backend slice from `ONBOARDING_SUBSTEM.md` plus structural alignment with `AGENTS.md`.

Completed so far:

- Authoritative `backend/`, `worker/`, and `frontend/` structure from `AGENTS.md`.
- FastAPI backend with health/readiness routes.
- JWT bearer-token dependency and role checks.
- SQLAlchemy models for organizations, users, brands, profiles, knowledge sources/chunks, integrations, jobs, and audit logs.
- Alembic migration for the onboarding subsystem.
- Brand creation API for crawl/manual paths.
- Tenant-scoped brand listing and brand summary.
- Manual Brand DNA profile submission.
- Profile patching only during `PENDING_REVIEW`.
- Admin-only approval that locks the profile and marks the brand `READY`.
- Job status endpoint.
- WordPress integration provider boundary plus Shopify/Webflow/custom stubs.
- Fernet credential encryption service.
- RQ worker entrypoint and stable task import targets.
- Next.js admin route skeleton for brand list and brand creation.
- Shared Brand DNA JSON schema and backend schema file.
- Prompt ownership folders plus backend Brand DNA v1 prompts.
- Docker Compose services for local Postgres and Redis.
- Architecture docs for repo structure and domain boundaries.
- Dev helper scripts for the API and worker.

Verified so far:

- Backend tests pass with `PYTHONPATH=backend python -m pytest -p no:rerunfailures backend/tests -q`.
- JSON files validate with `python -m json.tool`.

Not done yet:

- Dependency installation.
- Real login endpoint and password hashing.
- Redis enqueue wiring for crawl jobs.
- Crawler implementation.
- LLM extraction worker.
- Pinecone ingestion worker.
- Source upload/presigned URL endpoint.
- WordPress integration API route.
- Full admin panel forms and polling.
- Pinecone integration.
- Provider API integrations.
- Blog generation pipeline.
- CMS publishing implementation.

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

## Local Services

```bash
cp .env.example .env
docker compose up -d postgres redis
```

## Development Targets

Install dependencies first once package management is finalized:

```bash
pnpm install
```

Then run services:

```bash
pnpm --filter web dev
./scripts/dev-api.sh
./scripts/dev-worker.sh
```

## First Engineering Slice

Next implementation target:

1. Wire Redis/RQ enqueueing for `brand.onboard` and `brand.ingest`.
2. Implement crawler URL discovery, extraction, and source persistence.
3. Implement OpenRouter extraction with schema validation and retry.
4. Implement Pinecone ingestion and chunk reconciliation.
5. Add source upload/presigned URL and WordPress integration endpoints.
6. Expand the frontend admin panel beyond the current route skeleton.

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
