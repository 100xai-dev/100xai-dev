# AGENTS.md

**Purpose:** This file tells coding agents (Cursor, Claude Code, Windsurf, Codex, etc.) how to work in this codebase. Read it before making any change.

---

## 1. What This Project Is

**100xAI** is a multi-tenant AI marketing platform that learns a client's brand and generates/publishes blogs, LinkedIn content, and WhatsApp updates on their behalf. Onboarding is performed by the internal team — not by clients.

The codebase is a monorepo with three deployable units:

- `backend/` — FastAPI HTTP server (Python 3.11+)
- `worker/` — RQ worker process for async jobs (Python 3.11+)
- `frontend/` — Next.js 14 App Router admin panel (TypeScript)

Plus shared docs and migrations.

---

## 2. Source of Truth — Read These First

**These documents are authoritative. Implementations must match them. If a doc and the code conflict, the doc wins until the doc is updated.**

| File | What it covers |
|---|---|
| `PLAN.md` | Master plan for the whole product. Scope freeze, phasing, decisions. |
| `ONBOARDING_FOUNDATION.md` | Detailed spec for the onboarding subsystem (current scope). Data model, APIs, state machines, day-by-day plan, acceptance criteria. |

Future subsystem specs (blog pipeline, LinkedIn, WhatsApp) will be added as separate `*_FOUNDATION.md` files. When they appear, treat them the same way.

**Before doing anything**, scan the relevant foundation doc for the section that covers your task. The spec is the contract.

---

## 3. Repo Structure

```
.
├── PLAN.md                          # master plan
├── ONBOARDING_FOUNDATION.md         # onboarding spec (authoritative)
├── AGENTS.md                        # this file
├── README.md
├── docker-compose.yml               # local dev: Postgres + Redis
├── .env.example                     # required env vars
├── backend/
│   ├── alembic/                     # DB migrations
│   ├── app/
│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── config.py                # Pydantic Settings
│   │   ├── db.py
│   │   ├── deps.py                  # FastAPI dependencies
│   │   ├── auth/                    # JWT + RBAC
│   │   ├── routers/                 # API endpoints
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response models
│   │   ├── repositories/            # DB query layer (tenant-scoped)
│   │   ├── services/                # business logic
│   │   ├── integrations/            # external provider adapters (WP, etc.)
│   │   └── utils/
│   ├── prompts/                     # versioned LLM prompts
│   │   └── brand_dna/v1/
│   └── tests/
├── worker/
│   ├── main.py                      # RQ worker entrypoint
│   └── tasks/                       # job functions
└── frontend/
    ├── app/                         # Next.js App Router pages
    ├── components/
    ├── lib/
    └── package.json
```

---

## 4. Tech Stack (Locked — Do Not Substitute)

| Concern | Choice |
|---|---|
| Backend lang | Python 3.11+ |
| Backend framework | FastAPI |
| ORM | SQLAlchemy 2.x (sync session pattern for now; async if explicitly approved) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| DB | PostgreSQL 15+ |
| Cache / Queue | Redis 7+ |
| Job queue | RQ (not Celery) |
| Vector DB | Pinecone (namespace per brand) |
| LLM gateway | OpenRouter |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| Crawler | Playwright (Chromium) + trafilatura |
| Encryption | `cryptography.fernet.Fernet` |
| Object storage | S3-compatible (env-configurable; MinIO for dev) |
| Frontend | Next.js 14 App Router, TypeScript, Tailwind, ShadCN |
| Server state | React Query (or SWR — pick one and stick with it) |
| HTTP client (Python) | `httpx` (async) |

**Do not introduce new dependencies without listing them in the PR description and explaining why.** Prefer the stack above. If something is missing, ask before adding.

---

## 5. Working Principles

These are the rules the codebase is built on. Treat them as load-bearing.

### 5.1 The spec is the contract

If `ONBOARDING_FOUNDATION.md` says a field is named `audience_personas`, it is `audience_personas` — not `personas`, `audiences`, or `target_personas`. Match names, types, enum values, and shapes exactly.

When the spec is ambiguous: prefer the literal reading, then check the Decisions Log (§23 in the foundation doc), then ask. **Never invent behavior that isn't specified.**

### 5.2 Tenant scoping is non-negotiable

Every query that touches `brands`, `brand_profiles`, `brand_knowledge_sources`, `brand_knowledge_chunks`, `integration_accounts`, `integration_tokens`, or `audit_logs` **must filter by `org_id`**. The `org_id` comes from the authenticated user's JWT — never from request body or path params.

```python
# YES
db.query(Brand).filter(Brand.id == brand_id, Brand.org_id == current_user.org_id).first()

# NO (cross-tenant leak)
db.query(Brand).filter(Brand.id == brand_id).first()
```

A missing tenant filter is treated as a P0 bug. Repositories must enforce this — direct ORM queries in routers/services should be reviewed against this rule.

### 5.3 Async is the default for I/O

External calls (LLM, Pinecone, S3, HTTP fetches, Playwright) are async. Use `httpx.AsyncClient`, not `requests`. Use `async def` for any function that does I/O.

Worker tasks are sync at the top level (RQ requirement) — wrap async logic with `asyncio.run()` inside the task entrypoint.

### 5.4 Jobs do not block the API

Anything that takes more than ~500ms goes through the queue. The API enqueues a job and returns immediately with a `job_id`. The frontend polls for status.

Never call the LLM, crawler, or Pinecone from inside an HTTP request handler.

### 5.5 Errors are explicit

- Use typed exceptions (`RecoverableError`, `UnrecoverableError`, etc. — see foundation doc §15.5)
- HTTP errors return structured JSON: `{detail: "..."}` for human-readable, `{detail: [...]}` for validation
- Worker errors write to `jobs.error_message` and `audit_logs` — never to stdout alone

### 5.6 Logs do not contain secrets

Never log:
- API keys
- JWT tokens
- WordPress application passwords
- Encryption keys
- Raw integration credentials

The encryption helpers in `app/services/encryption.py` are the only place credentials get decrypted, and that decryption is scoped to immediate use — don't pass plaintext credentials around.

### 5.7 Migrations are forward-only

Every schema change is an Alembic migration. Never modify an existing migration that has been committed — write a new one. Migration filenames follow `{date}_{seq}_{description}.py`.

### 5.8 Prompts are versioned, not edited

Prompts live in `backend/prompts/{domain}/{version}/`. Once a version directory has been used in production (any `brand_profiles.prompt_version` reference exists), it is **frozen**. Changes go in a new version directory.

To bump a version:

1. Copy `v1/` → `v2/`
2. Edit `v2/` files
3. Update `system_notes.md` in `v2/` with a changelog
4. Update the env var or config that selects the active version

Do not edit `v1/*.txt` in place if there is any chance it has been used.

### 5.9 No client editing of locked profiles

Once `brand_profiles.locked = true`, the row is immutable. The PATCH endpoint must return 409 in this state. The frontend must hide edit affordances. The only way to change a locked profile is to hard-delete the brand and re-onboard.

### 5.10 Hard delete cascades all the way

When a brand is rejected, the deletion service must:

1. Revoke external integration tokens where applicable
2. Clear the Pinecone namespace
3. Delete S3 objects under the brand's prefix
4. Delete the Postgres `brands` row (cascade removes everything else)
5. Write an `audit_logs` entry with a snapshot of the deleted brand

If any of steps 1-3 fail, **do not delete the Postgres row.** Orphaned vectors or files are worse than a "stuck" brand record — ops can clean up manually.

---

## 6. Code Conventions

### 6.1 Python

- Format with `ruff format` (line length 100)
- Lint with `ruff check`
- Type-annotate every function signature (parameters and return)
- Use `from __future__ import annotations` at the top of modules if you need forward references
- Use `pathlib.Path`, not `os.path`
- Naming: `snake_case` for everything (variables, functions, modules, fields)
- Pydantic models: `PascalCase` for the class, `snake_case` for fields
- Enum values: `UPPER_SNAKE_CASE` for status enums (`READY`, `PENDING_REVIEW`), `lower_snake_case` for type enums (`crawled_page`, `manual_text`)
- Imports grouped: stdlib → third-party → first-party, with blank lines between
- Don't use `print()` outside scripts — use the `logger` from `app/logging.py`

### 6.2 TypeScript / Next.js

- Format with Prettier (default config)
- Use Server Components by default; mark Client Components with `'use client'` only when needed (forms, state, polling)
- Naming: `camelCase` for variables/functions, `PascalCase` for components and types, `kebab-case` for file names (e.g. `brand-list.tsx`)
- API types: prefer generating from OpenAPI; if hand-written, keep them in `lib/types.ts`
- Avoid `any`; use `unknown` and narrow if you must accept arbitrary input
- Components should accept their data via props — don't fetch inside leaf components

### 6.3 SQL / Postgres

- Identifiers: `snake_case`, no quotes
- Tables: plural noun (`brands`, `brand_profiles`)
- Primary keys: `id` (uuid)
- Foreign keys: `{singular_table}_id` (`brand_id`, `user_id`)
- Timestamps: `created_at`, `updated_at`, suffix `_at` for all timestamps
- Enums stored as `text` with `CHECK (col IN (...))` — not native Postgres enums (easier migrations)

### 6.4 API responses

- Snake-case field names in JSON (matches Python)
- Frontend transforms to camelCase at the API client boundary if desired
- Timestamps: ISO 8601 strings (UTC, `Z` suffix)
- UUIDs: lowercase string form
- Pagination (when added): `{items: [...], page: 1, page_size: 50, total: 123}`

---

## 7. Database Changes

1. Update the SQLAlchemy model in `backend/app/models/`
2. Generate a migration: `alembic revision --autogenerate -m "describe change"`
3. **Read the generated migration.** Autogenerate misses things (CHECK constraints, custom indexes, default values). Fix by hand.
4. Test up + down: `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`
5. Update affected repositories and Pydantic schemas

Never bypass Alembic — no raw `CREATE TABLE` outside migrations.

---

## 8. Tests

### 8.1 What to test

- **Always:** new utility functions (pure functions), state machine transitions, schema validation
- **Always:** new API endpoints (at least the happy path)
- **Often:** new repository methods if they have non-trivial filtering
- **Rarely:** trivial getters, framework boilerplate

### 8.2 Test structure

```
backend/tests/
├── unit/        # pure functions, no I/O
├── integration/ # full flows with fakes for LLM/Pinecone/HTTP
└── fixtures/    # sample HTML, sample LLM outputs, etc.
```

### 8.3 Test commands

```bash
# All tests
cd backend && pytest

# Just unit
pytest tests/unit

# With coverage
pytest --cov=app

# Single test file
pytest tests/unit/test_url_ranking.py

# Single test
pytest tests/unit/test_url_ranking.py::test_homepage_always_included
```

### 8.4 Mocks for external services

- LLM: use the `FakeLLMService` in `tests/fakes/llm.py` (foundation doc §20.3)
- Pinecone: use the in-memory `FakePineconeIndex` (foundation doc §20.4)
- HTTP (WordPress, etc.): use `respx` for httpx mocking
- Playwright: serve fixture HTML from a local Python http.server

Never call real external services from tests.

---

## 9. Common Tasks — Cheat Sheet

### 9.1 Add a new API endpoint

1. Define the request/response Pydantic models in `app/schemas/`
2. Add the route handler in the appropriate `app/routers/` file
3. Implement the business logic in `app/services/`
4. Use a tenant-scoped repository method for any DB access
5. Add audit log writes for state-changing actions
6. Write at least one happy-path test in `tests/integration/`
7. Verify it shows up in `/docs` (OpenAPI)

### 9.2 Add a new worker task

1. Define the task function in `worker/tasks/`
2. Decorate or wrap with the standard error handler (`RecoverableError` → retry, `UnrecoverableError` → fail)
3. Update job status (`jobs.update`) at meaningful checkpoints — frontend polling depends on this
4. Add a service function that enqueues it (`app/services/jobs.py`)
5. Write an integration test that exercises the task end-to-end with fakes

### 9.3 Add a new integration provider

1. Create a class in `app/integrations/{provider}.py` extending `IntegrationProvider`
2. Implement `validate_config`, `test_connection`, `publish`, `revoke`
3. Register in `app/integrations/registry.py`
4. Add the provider to the `integration_accounts.provider` CHECK constraint (new migration)
5. Add the provider to the `publish_adapter` enum if it's a CMS
6. Add a setup form component on the frontend
7. Add at least a connection test integration test

### 9.4 Update the brand profile schema

1. Add the column in a new Alembic migration
2. Update the SQLAlchemy model
3. Update the Pydantic models in `app/schemas/brand_profile.py`
4. Update `app/schemas/brand_profile_v1.json` (or bump to `v2.json` if it's a breaking change)
5. Update the extraction prompt to produce the new field (bump prompt version if behavior changes)
6. Update the admin panel form to display/edit the new field
7. Update the foundation doc §6 and add a Decisions Log entry

### 9.5 Run the stack locally

```bash
# Start dependencies (Postgres + Redis)
docker-compose up -d

# Migrate DB
cd backend && alembic upgrade head

# Backend API (terminal 1)
cd backend && uvicorn app.main:app --reload

# Worker (terminal 2)
cd worker && python main.py

# Frontend (terminal 3)
cd frontend && npm run dev
```

---

## 10. Things NOT to Do

- ❌ Do not introduce new top-level dependencies without listing them in the PR description.
- ❌ Do not modify a prompt in `v1/` once it has been used. Bump to `v2/` instead.
- ❌ Do not skip tenant scoping in any query against brand-related tables.
- ❌ Do not put LLM/Pinecone/Playwright calls inside HTTP request handlers — they go through the worker.
- ❌ Do not edit existing Alembic migrations. Create new ones.
- ❌ Do not soft-delete brands. Hard delete cascades through Pinecone, S3, and Postgres.
- ❌ Do not allow editing of a brand profile when `locked = true`. PATCH must 409.
- ❌ Do not use Celery, Airflow, Temporal, or any other workflow tool. RQ only.
- ❌ Do not commit `.env`. Use `.env.example` to document required vars.
- ❌ Do not log secrets, JWTs, application passwords, or encryption keys.
- ❌ Do not use `requests`. Use `httpx`.
- ❌ Do not assume the frontend will be public. It is admin-only.
- ❌ Do not add a clients table separate from brands. `brand_profiles` *is* the ClientProfile.
- ❌ Do not "improve" the spec by adding fields or endpoints not described in the foundation doc. If it's needed, propose it as a decision log entry first.

---

## 11. When Stuck or Unsure

In order of preference:

1. **Re-read the relevant foundation doc section.** Most ambiguity is resolved here.
2. **Check the Decisions Log** (§23 of `ONBOARDING_FOUNDATION.md`). Why was something done this way? It's probably listed.
3. **Look for analogous existing code.** Pattern-match against what's already in the repo (especially repositories and services).
4. **Ask the human.** Don't invent behavior to fill a gap.

When you do ask, ask specifically. Bad: "How should brand status work?" Good: "The spec says manual-path brands skip CRAWLING/EXTRACTING — should they enter INGESTING immediately on profile submission, or jump straight to PENDING_REVIEW if no sources need ingestion?"

---

## 12. Definition of Done (Per PR)

A PR is ready when:

- [ ] Code changes match what the spec describes (or the spec has been updated first)
- [ ] All tenant-scoped queries filter by `org_id`
- [ ] No secrets in code, commits, or logs
- [ ] Migrations run up and down cleanly
- [ ] New endpoints have at least one happy-path test
- [ ] New utility/business-logic functions have unit tests where they make sense
- [ ] `ruff check` and `ruff format` pass on backend code
- [ ] Frontend builds (`npm run build`) without errors or warnings beyond known ones
- [ ] Manual smoke test of the changed flow has been performed (or marked N/A with reason)
- [ ] PR description references the relevant spec section(s)

---

## 13. Quick Reference — Spec Sections

| If you're working on... | Read... |
|---|---|
| Data model / migrations | `ONBOARDING_FOUNDATION.md` §4 |
| Brand state transitions | §5 |
| Brand profile fields | §6 |
| API endpoint shapes | §7 |
| Crawler logic | §8 |
| Manual path | §9 |
| LLM extraction | §10 |
| Pinecone | §11 |
| Integration framework | §12 |
| WordPress specifically | §13 |
| Admin panel screens | §14 |
| Worker / RQ | §15 |
| Prompts | §16 |
| Security / RBAC | §17 |
| Folder structure | §18 |
| Environment vars | §19 |
| Testing | §20 |

---

**End of AGENTS.md**

If something in this file conflicts with `ONBOARDING_FOUNDATION.md`, the foundation doc wins. Update this file when conventions change.

## vexp <!-- vexp v2.0.24 -->

**MANDATORY: use `run_pipeline` - do NOT grep or glob the codebase.**
vexp returns pre-indexed, graph-ranked context in a single call.

### Workflow
1. `run_pipeline` with your task description - ALWAYS FIRST (replaces all other tools)
2. Make targeted changes based on the context returned
3. `run_pipeline` again only if you need more context

### Available MCP tools
- `run_pipeline` - **PRIMARY TOOL**. Runs capsule + impact + memory in 1 call.
  Auto-detects intent. Includes file content. Example: `run_pipeline({ "task": "fix auth bug" })`
- `get_skeleton` - compact file structure
- `index_status` - indexing status
- `expand_vexp_ref` - expand V-REF placeholders in v2 output

### Agentic search
- Do NOT use built-in file search, grep, or codebase indexing - always call `run_pipeline` first
- If you spawn sub-agents or background tasks, pass them the context from `run_pipeline`
  rather than letting them search the codebase independently

### Smart Features
Intent auto-detection, hybrid ranking, session memory, auto-expanding budget.

### Multi-Repo
`run_pipeline` auto-queries all indexed repos. Use `repos: ["alias"]` to scope. Run `index_status` to see aliases.
<!-- /vexp -->