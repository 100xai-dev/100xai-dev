# 100xAI

AI marketing platform for onboarding brands, generating persistent Brand DNA, producing SEO/AEO blogs, publishing to CMS channels, and distributing approved content across LinkedIn and WhatsApp.

## Current Status

The base repo skeleton has been created. This is not a finished product yet; it is the foundation for the first implementation slice.

Completed so far:

- Monorepo structure for frontend, backend, worker, shared schemas, prompts, docs, and infra.
- FastAPI backend skeleton with health and readiness routes.
- Placeholder brand creation API contract.
- Async job state enums for future crawl, blog, approval, publish, LinkedIn, and WhatsApp workflows.
- CMS publishing adapter contract so WordPress, Shopify, Webflow, and custom CMS connectors can share one interface.
- Redis worker package skeleton.
- Next.js frontend skeleton with a simple product module overview page.
- Shared Brand DNA JSON schema.
- Prompt ownership folders for Brand DNA, blogs, LinkedIn, WhatsApp, and images.
- Docker Compose services for local Postgres and Redis.
- Architecture docs for repo structure and domain boundaries.
- Dev helper scripts for the API and worker.

Verified so far:

- Python source compiles with `python -m compileall apps/api/src apps/worker/src`.
- JSON files validate with `python -m json.tool`.

Not done yet:

- Dependency installation.
- Real database models and migrations.
- Authentication.
- Persistent brand creation.
- Crawl job queueing.
- Pinecone integration.
- Provider API integrations.
- Blog generation pipeline.
- CMS publishing implementation.

## Repo Layout

```text
apps/
  web/        Next.js frontend
  api/        FastAPI backend and domain services
  worker/     async worker entrypoints
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

1. Add real SQLAlchemy models for users, organizations, brands, brand profiles, knowledge sources, jobs, and audit logs.
2. Add Alembic migrations.
3. Implement `POST /v1/brands` with database persistence.
4. Create a crawl job when a brand is submitted.
5. Add onboarding UI for brand name, website URL, industry, notes, and upload placeholder.
6. Prepare the Brand DNA generation boundary using `packages/shared-schemas/brand-dna/schema.json`.

## Important Files

- `apps/api/src/ai_brand_os/main.py`: FastAPI app factory.
- `apps/api/src/ai_brand_os/api/v1.py`: current v1 API routes.
- `apps/api/src/ai_brand_os/jobs/states.py`: shared job state enums.
- `apps/api/src/ai_brand_os/integrations/publishing.py`: CMS publish adapter contract.
- `apps/web/src/app/page.tsx`: current frontend entry page.
- `apps/worker/src/ai_brand_os_worker/main.py`: worker entrypoint placeholder.
- `packages/shared-schemas/brand-dna/schema.json`: Brand DNA contract.
- `packages/prompts/`: prompt files owned by the prompt/content workflow.
- `docs/architecture/domain-boundaries.md`: domain boundary reference.
- `docs/architecture/repo-architecture.md`: repo architecture reference.
