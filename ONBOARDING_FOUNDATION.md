finalized.md 
# 100xAI — Onboarding & Brand DNA Foundation Specification

**Version:** 1.0
**Status:** Authoritative — this document is the source of truth for the onboarding subsystem
**Scope:** Client onboarding workflow, brand DNA construction (crawl and manual paths), knowledge ingestion, publishing integrations, admin panel
**Audience:** Engineering team and AI coding agents implementing the onboarding subsystem
**Out of scope:** Blog generation pipeline, LinkedIn workflows, WhatsApp campaigns, analytics dashboard

---

## How to Read This Document

This document is structured as an implementation contract. Sections progress from concepts → data → contracts → algorithms → implementation guidance. Read sequentially the first time.

- **Frozen decisions** are statements without qualification — implement them as written.
- **Recommended defaults** can be changed if there is a written reason to do so. Defaults are listed with rationale.
- **Pseudocode** is illustrative, not prescriptive. Implementations may differ in syntax but must preserve semantics.
- **JSON shapes** are contracts. Implementations must produce/accept exactly these shapes.
- **All identifiers** use `snake_case` for database, API JSON, and Python. Frontend code uses `camelCase`; an explicit transformation layer handles the boundary.

### Conventions

- IDs are UUID v4 unless otherwise noted, stored as `uuid` in Postgres.
- Timestamps are `timestamptz` (UTC), serialized as ISO 8601 in JSON.
- Enums are stored as Postgres `text` with a `CHECK` constraint, not as native Postgres enums. This makes migrations easier.
- All tables have `created_at` and `updated_at` columns (`timestamptz NOT NULL DEFAULT now()`).
- Soft delete is **not used** in this subsystem. When a brand is rejected/deleted, the rows are hard-deleted along with associated Pinecone vectors. This is intentional — see Section 5.3.

---

## Table of Contents

0. [Document Purpose](#0-document-purpose)
1. [System Scope and Boundaries](#1-system-scope-and-boundaries)
2. [Core Concepts](#2-core-concepts)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Model](#4-data-model)
5. [State Machines and Lifecycles](#5-state-machines-and-lifecycles)
6. [Brand Profile Schema](#6-brand-profile-schema)
7. [API Contracts](#7-api-contracts)
8. [Brand DNA — Crawl Path](#8-brand-dna--crawl-path)
9. [Brand DNA — Manual Path](#9-brand-dna--manual-path)
10. [Extraction Worker](#10-extraction-worker)
11. [Pinecone Ingestion](#11-pinecone-ingestion)
12. [Integration Framework](#12-integration-framework)
13. [WordPress Integration (First Connector)](#13-wordpress-integration-first-connector)
14. [Admin Panel](#14-admin-panel)
15. [Job and Worker Framework](#15-job-and-worker-framework)
16. [Prompts and Prompt Governance](#16-prompts-and-prompt-governance)
17. [Security and Multi-Tenancy](#17-security-and-multi-tenancy)
18. [Folder Structure](#18-folder-structure)
19. [Environment Configuration](#19-environment-configuration)
20. [Testing Strategy](#20-testing-strategy)
21. [Implementation Plan (Day-by-Day)](#21-implementation-plan-day-by-day)
22. [Acceptance Criteria](#22-acceptance-criteria)
23. [Decisions Log](#23-decisions-log)
24. [Glossary](#24-glossary)

---

## 0. Document Purpose

This specification defines everything required to build the onboarding subsystem of 100xAI. The onboarding subsystem provisions a new client into the platform such that downstream pipelines (blog generation, LinkedIn, WhatsApp) can operate on the client's brand.

A successful onboarding produces:

1. A locked `brand_profiles` row matching the Pillar Blog Engine ClientProfile contract.
2. A populated Pinecone namespace containing the client's knowledge for RAG retrieval.
3. One or more connected `integration_accounts` for publishing channels (at minimum, the WordPress CMS for blog publishing — others added later).
4. An audit trail capturing what happened during onboarding.

If any of these is missing or partial, the brand is not considered onboarded.

---

## 1. System Scope and Boundaries

### 1.1 In Scope

- Multi-tenant brand creation
- Two-path brand DNA construction (crawl-based and manual form-based)
- Website crawling, content extraction, and normalization
- LLM-based brand DNA generation from crawled content
- Schema validation of generated brand profiles
- Pinecone vector ingestion of brand knowledge sources
- Admin panel for the internal team to operate onboarding
- WordPress integration setup (auth, connection test, encrypted credential storage)
- Operational configuration fields (Placid template ID, image bucket, defaults)
- Brand approval-and-lock workflow
- Hard reject / delete brand workflow
- Audit logging of state transitions and team actions

### 1.2 Out of Scope (Built Later)

- Blog generation pipeline (Pillar Blog Engine — separate spec)
- LinkedIn workflows (separate spec)
- WhatsApp campaign workflows (separate spec)
- Analytics dashboard
- Shopify, Webflow, and custom CMS connector UIs (adapter stubs only)
- Client-facing portal (Phase 1 has no client login; team operates everything)
- Editing a locked brand profile (not supported — must hard-delete and re-onboard)

### 1.3 Hard Constraints

- Onboarding is performed by the internal team during a discovery call. No public self-serve flow exists.
- Once a brand profile is locked (status = `READY`), it is immutable. The only way to change it is to delete the brand and create a new one.
- Brand DNA is created **once** per brand and never iterated. The team reviews and edits the AI-generated profile during the `PENDING_REVIEW` state, then locks it. After locking, no edits.
- Blog content follows a separate "approve or restart" rule (see Pillar Blog Engine spec). Brand DNA does **not** follow this rule — the team has full edit capability during the `PENDING_REVIEW` window.

---

## 2. Core Concepts

### 2.1 Brand

A brand represents a single client tenant. One client may, in future, have multiple brands (sub-brands, product lines), but Phase 1 assumes one brand per client.

### 2.2 BrandProfile (= ClientProfile)

The single source of client truth. Every downstream pipeline reads from this record. It contains both AI-generated fields (extracted during onboarding) and team-configured operational fields (set manually during onboarding).

This record's contract aligns with the ClientProfile contract defined in the Pillar Blog Engine specification. They are **the same record** — there is no separate ClientProfile table. The Pillar engine's `{{client.field}}` placeholders resolve against this table.

### 2.3 Knowledge Source

A single input artifact for a brand: a crawled web page, an uploaded document, a manually entered long-form text block. Knowledge sources are the raw material from which the brand profile is constructed and which feed Pinecone for RAG retrieval.

### 2.4 Knowledge Chunk

A subdivision of a knowledge source's normalized text, sized for embedding (target ~800 tokens). Each chunk corresponds to one Pinecone vector and one row in `brand_knowledge_chunks`.

### 2.5 Integration Account

A connection between a brand and an external service (CMS, social platform, messaging provider). Stores configuration; credentials live in the related `integration_tokens` table (encrypted).

### 2.6 Job

An async unit of work executed by a worker. Onboarding uses jobs for crawling, extraction, and ingestion. Each job has a status, a stage, and metadata.

### 2.7 Brand Readiness vs Channel Readiness

These are **independent**:

- **Brand readiness** = the brand profile is locked. Tracked by `brands.status = READY`.
- **Channel readiness** = an `integration_accounts` row exists and is active for a given channel.

A brand can be `READY` with zero channels connected (LinkedIn pipeline still works against brand profile data without CMS). A brand cannot use blog publishing until both: brand is `READY` AND a CMS integration is connected.

### 2.8 Two-Path Brand DNA

Brand DNA can be constructed via:

- **Crawl path** (`dna_source = 'crawl'`): website URL → crawler → LLM extraction → profile
- **Manual path** (`dna_source = 'manual'`): team fills profile form directly → no crawl, no extraction → optional uploaded docs ingested as knowledge sources

Both paths produce the same `brand_profiles` row shape. Both paths ingest knowledge sources into Pinecone. The only difference is whether the AI extraction step runs.

---

## 3. Architecture Overview

### 3.1 Components

```
┌───────────────────────────────────────────────────────────────┐
│                   Next.js Admin Panel (Frontend)              │
│        (Team-facing only — no public-facing surface)          │
└──────────────────────────────┬────────────────────────────────┘
                               │ HTTPS / JSON
┌──────────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                            │
│  ┌─────────┬──────────┬───────────┬───────────┬────────────┐  │
│  │  auth   │  brands  │ brand_dna │ integrations│ jobs API │  │
│  └─────────┴──────────┴───────────┴───────────┴────────────┘  │
└──────────┬───────────────────────────┬────────────────────────┘
           │                           │
           │ enqueue                   │ read/write
           ▼                           ▼
┌──────────────────┐         ┌──────────────────┐
│  Redis (queue)   │         │   PostgreSQL     │
└──────────┬───────┘         └──────────────────┘
           │
           │ pick up jobs
           ▼
┌────────────────────────────────────────────────────────────┐
│                     Worker Process(es)                      │
│  ┌────────────┬────────────────┬──────────────────────┐    │
│  │  crawler   │  extractor     │  pinecone_ingester   │    │
│  └────────────┴────────────────┴──────────────────────┘    │
└─────┬──────────────────────────────────────┬──────────────┘
      │                                      │
      ▼                                      ▼
┌──────────────┐                       ┌──────────────┐
│  Playwright  │                       │  Pinecone    │
│  (headless)  │                       │  (vector DB) │
└──────────────┘                       └──────────────┘
           │                                  ▲
           │                                  │
           ▼                                  │
┌──────────────────┐         ┌──────────────────────┐
│  OpenRouter      │◄────────┤  Embedding Model     │
│  (LLM gateway)   │         │  (text-embedding-3-  │
└──────────────────┘         │   small)             │
                             └──────────────────────┘

┌──────────────────────────────────────────────────────────┐
│   S3-Compatible Object Storage (uploads, exports)        │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Tech Stack (Locked)

| Layer | Technology |
|---|---|
| Frontend | Next.js 14+ (App Router), TypeScript, Tailwind, ShadCN UI |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL 15+ |
| Vector DB | Pinecone (namespace-per-brand model) |
| Queue | Redis 7+ with RQ (Python) |
| LLM Gateway | OpenRouter (provider-agnostic) |
| Embedding Model | OpenAI `text-embedding-3-small` (1536 dimensions) |
| Crawler | Playwright (Chromium headless) + trafilatura for extraction |
| Object Storage | S3-compatible (S3, R2, or MinIO for dev) |
| Auth | JWT-based, custom (RBAC) |
| Token Encryption | `cryptography.fernet.Fernet` symmetric encryption |

### 3.3 External Service Dependencies

| Service | Purpose | Where Configured |
|---|---|---|
| OpenRouter | LLM calls for brand DNA extraction | `OPENROUTER_API_KEY` |
| OpenAI | Embedding generation | `OPENAI_API_KEY` (separate from extraction LLM) |
| Pinecone | Vector storage | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` |
| S3-compatible | File uploads, exports | `S3_*` env vars |

### 3.4 Service Boundaries

- **API server**: Stateless. Handles HTTP, validates input, persists to DB, enqueues jobs, returns responses. Never blocks on long operations.
- **Worker**: Stateful (in the sense of pulling from queue). Performs all crawling, LLM calls, Pinecone operations. Communicates back via DB writes.
- **DB**: Source of truth for operational data. Jobs, profiles, audit logs all live here.
- **Pinecone**: Source of truth for embeddings only. Postgres `brand_knowledge_chunks` table is the reconciliation record for what should be in Pinecone.

---

## 4. Data Model

### 4.1 Tables Overview

This subsystem owns or extends these tables:

- `users` — extended (assumed minimal exists)
- `organizations` — extended (assumed minimal exists)
- `brands` — primary
- `brand_profiles` — primary
- `brand_knowledge_sources` — primary
- `brand_knowledge_chunks` — primary
- `integration_accounts` — primary
- `integration_tokens` — primary
- `jobs` — extended
- `audit_logs` — primary

### 4.2 Full DDL

```sql
-- ============================================================
-- USERS (assumed exists; shown for reference)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email           text NOT NULL UNIQUE,
    password_hash   text NOT NULL,
    name            text,
    role            text NOT NULL DEFAULT 'admin'
                        CHECK (role IN ('admin', 'team_member', 'viewer')),
    org_id          uuid NOT NULL REFERENCES organizations(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- ORGANIZATIONS (assumed exists; shown for reference)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- BRANDS
-- ============================================================
CREATE TABLE brands (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          uuid NOT NULL REFERENCES organizations(id),
    name            text NOT NULL,
    website_url     text,            -- nullable for manual path
    dna_source      text NOT NULL    -- 'crawl' | 'manual'
                        CHECK (dna_source IN ('crawl', 'manual')),
    status          text NOT NULL DEFAULT 'DRAFT'
                        CHECK (status IN (
                            'DRAFT',
                            'CRAWLING',
                            'EXTRACTING',
                            'INGESTING',
                            'PENDING_REVIEW',
                            'READY',
                            'FAILED'
                        )),
    failure_reason  text,            -- populated when status = FAILED
    created_by      uuid NOT NULL REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_brands_org_status ON brands(org_id, status);
CREATE INDEX idx_brands_created_at ON brands(created_at DESC);

-- ============================================================
-- BRAND_PROFILES
-- The locked DNA. One row per brand. Becomes the ClientProfile
-- record read by all downstream engines.
-- ============================================================
CREATE TABLE brand_profiles (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            uuid NOT NULL UNIQUE REFERENCES brands(id) ON DELETE CASCADE,

    -- AI-generated or team-edited content fields ---
    name                text NOT NULL,
    site_url            text,
    one_liner           text NOT NULL,
    industry            text,
    allowed_topics      text[] NOT NULL DEFAULT '{}',
    disallowed_topics   text[] NOT NULL DEFAULT '{}',
    audience_personas   text[] NOT NULL DEFAULT '{}',
    tone_rules          text NOT NULL,
    banned_phrases      text[] NOT NULL DEFAULT '{}',
    unique_angle        text NOT NULL,
    ctas                text[] NOT NULL DEFAULT '{}',
    proof_points        text[] NOT NULL DEFAULT '{}',
    messaging_guardrails text[] NOT NULL DEFAULT '{}',
    compliance_keywords text[] NOT NULL DEFAULT '{}',

    -- Visual identity fields ---
    image_subject_hints text,
    image_palette       text,
    visual_direction    text,

    -- Team-configured operational fields ---
    internal_links      jsonb NOT NULL DEFAULT '[]'::jsonb,
                            -- shape: [{label: string, url: string}, ...]
    placid_template_id  text,                     -- nullable until configured
    image_output_bucket text,                     -- nullable until configured
    default_location    text NOT NULL DEFAULT 'United States',
    default_language    text NOT NULL DEFAULT 'English',
    publish_adapter     text NOT NULL DEFAULT 'none'
                            CHECK (publish_adapter IN (
                                'none',
                                'wordpress',
                                'shopify',
                                'webflow',
                                'custom_api'
                            )),
    publish_config      jsonb NOT NULL DEFAULT '{}'::jsonb,
                            -- adapter-specific configuration

    -- Provenance ---
    generation_source   text NOT NULL             -- 'crawl' | 'manual' | 'hybrid'
                            CHECK (generation_source IN ('crawl', 'manual', 'hybrid')),
    prompt_version      text,                     -- e.g. 'v1' (null for manual)
    extraction_model    text,                     -- e.g. 'anthropic/claude-3-5-sonnet'
                                                  --   (null for manual)
    raw_extraction      jsonb,                    -- original LLM output before edits

    -- Lifecycle ---
    locked              boolean NOT NULL DEFAULT false,
    locked_at           timestamptz,
    locked_by           uuid REFERENCES users(id),

    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_brand_profiles_brand_id ON brand_profiles(brand_id);

-- ============================================================
-- BRAND_KNOWLEDGE_SOURCES
-- One row per input artifact (crawled page, uploaded doc, manual text).
-- ============================================================
CREATE TABLE brand_knowledge_sources (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    source_type     text NOT NULL
                        CHECK (source_type IN (
                            'crawled_page',
                            'uploaded_doc',
                            'manual_text',
                            'manual_form_field'
                        )),
    title           text,
    url             text,             -- for crawled_page
    storage_key     text,             -- for uploaded_doc (S3 key)
    raw_text        text,             -- full extracted text; nullable after purge
    normalized_text text NOT NULL,    -- cleaned, persisted indefinitely
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
                        -- e.g. {h1, meta_description, content_type, word_count}
    word_count      integer,
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    purge_at        timestamptz,      -- raw_text nulled out after this date
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_sources_brand ON brand_knowledge_sources(brand_id);
CREATE INDEX idx_knowledge_sources_purge ON brand_knowledge_sources(purge_at)
    WHERE purge_at IS NOT NULL AND raw_text IS NOT NULL;

-- ============================================================
-- BRAND_KNOWLEDGE_CHUNKS
-- Reconciliation table for Pinecone. One row per vector.
-- ============================================================
CREATE TABLE brand_knowledge_chunks (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id            uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    source_id           uuid NOT NULL REFERENCES brand_knowledge_sources(id)
                            ON DELETE CASCADE,
    chunk_index         integer NOT NULL,         -- 0-based within source
    text                text NOT NULL,
    token_count         integer NOT NULL,
    vector_id           text NOT NULL,            -- the Pinecone vector ID
    embedding_model     text NOT NULL,            -- e.g. 'text-embedding-3-small'
    namespace           text NOT NULL,            -- Pinecone namespace (brand_id as text)
    created_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, chunk_index)
);

CREATE INDEX idx_chunks_brand ON brand_knowledge_chunks(brand_id);
CREATE INDEX idx_chunks_source ON brand_knowledge_chunks(source_id);

-- ============================================================
-- INTEGRATION_ACCOUNTS
-- A connection between a brand and an external service.
-- ============================================================
CREATE TABLE integration_accounts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    provider        text NOT NULL
                        CHECK (provider IN (
                            'wordpress',
                            'shopify',
                            'webflow',
                            'custom_api',
                            'unipile_linkedin',
                            'vapi_whatsapp'
                        )),
    status          text NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'active', 'failed', 'revoked')),
    display_label   text,            -- e.g. "blog.acme.com"
    config          jsonb NOT NULL DEFAULT '{}'::jsonb,
                        -- non-secret configuration (URLs, IDs, settings)
    last_tested_at  timestamptz,
    last_error      text,
    created_by      uuid NOT NULL REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (brand_id, provider)
);

CREATE INDEX idx_integrations_brand ON integration_accounts(brand_id);

-- ============================================================
-- INTEGRATION_TOKENS
-- Encrypted credentials. Separated from accounts for security and
-- to allow rotation without modifying account records.
-- ============================================================
CREATE TABLE integration_tokens (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_account_id uuid NOT NULL UNIQUE REFERENCES integration_accounts(id)
                            ON DELETE CASCADE,
    encrypted_payload   bytea NOT NULL,           -- Fernet-encrypted JSON blob
    encryption_key_id   text NOT NULL,            -- e.g. 'v1' — supports rotation
    expires_at          timestamptz,              -- for OAuth refresh tokens
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- ============================================================
-- JOBS
-- Async work units.
-- ============================================================
CREATE TABLE jobs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id        uuid REFERENCES brands(id) ON DELETE CASCADE,
    job_type        text NOT NULL
                        CHECK (job_type IN (
                            'brand.onboard',         -- parent job for crawl path
                            'brand.crawl',           -- discrete stage
                            'brand.extract',         -- discrete stage
                            'brand.ingest'           -- discrete stage
                        )),
    status          text NOT NULL DEFAULT 'NEW'
                        CHECK (status IN (
                            'NEW',
                            'RUNNING',
                            'SUCCEEDED',
                            'FAILED'
                        )),
    stage           text,                          -- current sub-stage label
    progress        jsonb NOT NULL DEFAULT '{}'::jsonb,
                        -- free-form progress info: pages_crawled, sources_added
    input_payload   jsonb NOT NULL DEFAULT '{}'::jsonb,
    output_payload  jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message   text,
    error_details   jsonb,
    attempt_count   integer NOT NULL DEFAULT 0,
    max_attempts    integer NOT NULL DEFAULT 3,
    started_at      timestamptz,
    finished_at     timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_brand ON jobs(brand_id);
CREATE INDEX idx_jobs_status_type ON jobs(status, job_type);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);

-- ============================================================
-- AUDIT_LOGS
-- Append-only record of state changes and team actions.
-- ============================================================
CREATE TABLE audit_logs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          uuid NOT NULL REFERENCES organizations(id),
    user_id         uuid REFERENCES users(id),    -- null for system events
    brand_id        uuid REFERENCES brands(id) ON DELETE SET NULL,
    action          text NOT NULL,                -- e.g. 'brand.created',
                                                  -- 'brand.approved', 'brand.rejected'
    resource_type   text,                         -- e.g. 'brand', 'integration_account'
    resource_id     uuid,
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_brand ON audit_logs(brand_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_org ON audit_logs(org_id, created_at DESC);
```

### 4.3 Cascade Delete Behavior

`ON DELETE CASCADE` is set on all child tables of `brands`. Deleting a brand row removes:

- `brand_profiles` row
- All `brand_knowledge_sources` rows
- All `brand_knowledge_chunks` rows
- All `integration_accounts` (and their `integration_tokens`)
- All `jobs` for that brand

Audit logs use `ON DELETE SET NULL` on `brand_id` so logs survive deletion for compliance, but the FK is broken.

**Pinecone vectors are NOT deleted automatically by Postgres cascade.** The `delete_brand()` service function (Section 12.5) explicitly clears the Pinecone namespace before deleting the Postgres rows.

### 4.4 Retention Rules

- `brand_knowledge_sources.raw_text` is **nulled out** (not row-deleted) 14 days after `fetched_at` for sources where `source_type = 'crawled_page'`. A nightly worker handles this. Normalized text and metadata persist indefinitely.
- For `source_type IN ('uploaded_doc', 'manual_text', 'manual_form_field')`, `raw_text` is kept indefinitely (the client provided this material, so it's not third-party content).
- `jobs` rows are kept for 90 days then archived. Not implemented in this subsystem — note for future.

---

## 5. State Machines and Lifecycles

### 5.1 Brand Status State Machine

```
                                            ┌──────────────────┐
                                            │     DRAFT        │
                                            │   (just created) │
                                            └────────┬─────────┘
                                                     │
                              ┌──────────────────────┴──────────────────────┐
                              │ dna_source = 'crawl'       dna_source = 'manual'
                              ▼                                              ▼
                  ┌──────────────────┐                          ┌────────────────────┐
                  │    CRAWLING      │                          │  PENDING_REVIEW    │
                  │ (worker active)  │                          │ (team fills form)  │
                  └────────┬─────────┘                          └─────────┬──────────┘
                           │                                              │
                           ▼                                              │
                  ┌──────────────────┐                                    │
                  │   EXTRACTING     │                                    │
                  │ (LLM running)    │                                    │
                  └────────┬─────────┘                                    │
                           │                                              │
                           ▼                                              │
                  ┌──────────────────┐                                    │
                  │   INGESTING      │                                    │
                  │ (Pinecone upsert)│                                    │
                  └────────┬─────────┘                                    │
                           │                                              │
                           ▼                                              │
                  ┌──────────────────┐                                    │
                  │ PENDING_REVIEW   │                                    │
                  │ (team reviews)   │                                    │
                  └────────┬─────────┘                                    │
                           │                                              │
                           │           ┌──────────────────────────────────┘
                           │           │
                           ▼           ▼
                          ┌──────────────────┐
                          │   approve action │
                          │ (locks profile)  │
                          └────────┬─────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │     READY        │  ← terminal (success)
                          └──────────────────┘

  Any state → FAILED  (on unrecoverable error; recorded in failure_reason)
  Any state → (hard delete on reject action; row removed)
```

### 5.2 Allowed Transitions

| From | To | Trigger |
|---|---|---|
| (none) | `DRAFT` | `POST /v1/brands` creates the brand |
| `DRAFT` | `CRAWLING` | crawl job picks up (crawl path) |
| `DRAFT` | `PENDING_REVIEW` | manual profile submitted via `POST /v1/brands/:id/profile` |
| `CRAWLING` | `EXTRACTING` | crawl completes successfully |
| `CRAWLING` | `FAILED` | crawl fails unrecoverably |
| `EXTRACTING` | `INGESTING` | extraction completes and profile written |
| `EXTRACTING` | `FAILED` | extraction fails unrecoverably |
| `INGESTING` | `PENDING_REVIEW` | Pinecone ingestion completes |
| `INGESTING` | `FAILED` | ingestion fails unrecoverably |
| `PENDING_REVIEW` | `READY` | team approves via `POST /v1/brands/:id/approve` |
| any | (deleted) | team rejects via `DELETE /v1/brands/:id` |
| `FAILED` | (deleted) | team cleanup |

**No transition out of `READY`.** Once locked, a brand is immutable. Editing requires deletion and re-onboarding.

### 5.3 Why Hard Delete on Reject

Soft delete is intentionally not used because:

1. Rejection means the team has decided the brand is wrong. Keeping it around adds drift risk.
2. Pinecone cost: dormant vectors still consume storage.
3. Simpler reconciliation: every brand row corresponds to a live, queryable brand.

If "restore from trash" is ever needed, build a separate `archived_brands` mechanism. Not in this scope.

### 5.4 Job State Machine

```
NEW → RUNNING → SUCCEEDED
            └── FAILED (after max_attempts exhausted)
            └── RUNNING (re-attempt while attempts remain)
```

A worker picks up a `NEW` job and atomically transitions it to `RUNNING`, incrementing `attempt_count`. On exception, if `attempt_count < max_attempts`, the job goes back to `NEW` after backoff; otherwise `FAILED`.

---

## 6. Brand Profile Schema

### 6.1 Field Categories

**AI-Generated Fields** (extracted by LLM in crawl path; team-entered in manual path):

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | text | yes | Brand display name (e.g. "GoGrabJob") |
| `site_url` | text | yes (crawl) / no (manual) | Canonical website URL |
| `one_liner` | text | yes | One-sentence product description |
| `industry` | text | no | High-level industry classification |
| `allowed_topics` | text[] | yes | On-domain topics to keep (drives keyword filter) |
| `disallowed_topics` | text[] | no | Topics to explicitly reject |
| `audience_personas` | text[] | yes | Distinct audience descriptions (1+ required) |
| `tone_rules` | text | yes | Plain-English tone guidance |
| `banned_phrases` | text[] | yes | Phrases the LLM must never use |
| `unique_angle` | text | yes | Differentiator to lean on in content |
| `ctas` | text[] | yes | Approved CTAs (at least 1 required) |
| `proof_points` | text[] | no | Stats, social proof, credentials |
| `messaging_guardrails` | text[] | no | High-level messaging rules |
| `compliance_keywords` | text[] | no | Keywords requiring extra care (e.g. medical, legal) |
| `image_subject_hints` | text | no | What the brand's images typically depict |
| `image_palette` | text | no | Color description (e.g. "blue/teal accents (#2563EB, #0EA5E9)") |
| `visual_direction` | text | no | Overall visual style description |

**Team-Configured Operational Fields** (cannot be AI-extracted):

| Field | Type | Required | Description |
|---|---|---|---|
| `internal_links` | jsonb | no | Array of `{label, url}` for internal linking in blogs |
| `placid_template_id` | text | yes for blog publishing | Placid template ID for featured image composite |
| `image_output_bucket` | text | yes for blog publishing | S3 bucket/prefix where composited images go |
| `default_location` | text | yes | Default for keyword research (e.g. "United States") |
| `default_language` | text | yes | Default for content (e.g. "English") |
| `publish_adapter` | enum | yes | `none` / `wordpress` / `shopify` / `webflow` / `custom_api` |
| `publish_config` | jsonb | conditional | Adapter-specific config |

**Provenance Fields** (system-set, read-only):

| Field | Type | Description |
|---|---|---|
| `generation_source` | text | `crawl` / `manual` / `hybrid` |
| `prompt_version` | text | Which prompt version produced this (e.g. `v1`) |
| `extraction_model` | text | Which LLM produced this (e.g. `anthropic/claude-3-5-sonnet`) |
| `raw_extraction` | jsonb | Original LLM output before any team edits |
| `locked` | bool | True once approved |
| `locked_at` | timestamptz | When approval happened |
| `locked_by` | uuid | Who approved |

### 6.2 JSON Schema (used for validation)

Save as `backend/app/schemas/brand_profile_v1.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BrandProfile",
  "type": "object",
  "required": [
    "name",
    "one_liner",
    "allowed_topics",
    "audience_personas",
    "tone_rules",
    "banned_phrases",
    "unique_angle",
    "ctas"
  ],
  "properties": {
    "name": { "type": "string", "minLength": 1, "maxLength": 200 },
    "site_url": { "type": ["string", "null"], "format": "uri" },
    "one_liner": { "type": "string", "minLength": 10, "maxLength": 500 },
    "industry": { "type": ["string", "null"] },
    "allowed_topics": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "minLength": 1 }
    },
    "disallowed_topics": {
      "type": "array",
      "items": { "type": "string" }
    },
    "audience_personas": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "minLength": 1 }
    },
    "tone_rules": { "type": "string", "minLength": 10 },
    "banned_phrases": {
      "type": "array",
      "items": { "type": "string" }
    },
    "unique_angle": { "type": "string", "minLength": 5 },
    "ctas": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "minLength": 1 }
    },
    "proof_points": {
      "type": "array",
      "items": { "type": "string" }
    },
    "messaging_guardrails": {
      "type": "array",
      "items": { "type": "string" }
    },
    "compliance_keywords": {
      "type": "array",
      "items": { "type": "string" }
    },
    "image_subject_hints": { "type": ["string", "null"] },
    "image_palette": { "type": ["string", "null"] },
    "visual_direction": { "type": ["string", "null"] }
  },
  "additionalProperties": false
}
```

### 6.3 Pydantic Models (Python)

```python
# backend/app/schemas/brand_profile.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from datetime import datetime

class PublishAdapter(str, Enum):
    NONE = "none"
    WORDPRESS = "wordpress"
    SHOPIFY = "shopify"
    WEBFLOW = "webflow"
    CUSTOM_API = "custom_api"

class InternalLink(BaseModel):
    label: str
    url: HttpUrl

class BrandProfileContent(BaseModel):
    """The AI-generatable content portion of the profile."""
    name: str = Field(..., min_length=1, max_length=200)
    site_url: Optional[HttpUrl] = None
    one_liner: str = Field(..., min_length=10, max_length=500)
    industry: Optional[str] = None
    allowed_topics: List[str] = Field(..., min_items=1)
    disallowed_topics: List[str] = Field(default_factory=list)
    audience_personas: List[str] = Field(..., min_items=1)
    tone_rules: str = Field(..., min_length=10)
    banned_phrases: List[str] = Field(default_factory=list)
    unique_angle: str = Field(..., min_length=5)
    ctas: List[str] = Field(..., min_items=1)
    proof_points: List[str] = Field(default_factory=list)
    messaging_guardrails: List[str] = Field(default_factory=list)
    compliance_keywords: List[str] = Field(default_factory=list)
    image_subject_hints: Optional[str] = None
    image_palette: Optional[str] = None
    visual_direction: Optional[str] = None

class OperationalConfig(BaseModel):
    internal_links: List[InternalLink] = Field(default_factory=list)
    placid_template_id: Optional[str] = None
    image_output_bucket: Optional[str] = None
    default_location: str = "United States"
    default_language: str = "English"
    publish_adapter: PublishAdapter = PublishAdapter.NONE
    publish_config: Dict[str, Any] = Field(default_factory=dict)

class BrandProfileFull(BrandProfileContent, OperationalConfig):
    """Complete profile as returned by GET endpoint."""
    id: UUID
    brand_id: UUID
    generation_source: str
    prompt_version: Optional[str]
    extraction_model: Optional[str]
    locked: bool
    locked_at: Optional[datetime]
    locked_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
```

---

## 7. API Contracts

All endpoints under `/v1`. All endpoints require authentication (Bearer JWT). All endpoints are tenant-scoped by `org_id` extracted from the JWT.

### 7.1 Conventions

- Success: 2xx with JSON body
- Validation error: 422 with `{detail: [{loc, msg, type}]}`
- Auth error: 401 (no token) / 403 (insufficient role)
- Not found: 404 with `{detail: "resource not found"}`
- Conflict: 409 with `{detail: "..."}`
- Server error: 500 with `{detail: "internal error", request_id: "..."}`

All endpoints return a `request_id` in headers for tracing.

### 7.2 Endpoint List

| Method | Path | Purpose | Auth Role |
|---|---|---|---|
| POST | `/v1/brands` | Create a brand | admin, team_member |
| GET | `/v1/brands` | List brands in org | admin, team_member, viewer |
| GET | `/v1/brands/:id` | Get brand summary | admin, team_member, viewer |
| DELETE | `/v1/brands/:id` | Hard-delete brand | admin |
| POST | `/v1/brands/:id/sources` | Add knowledge source | admin, team_member |
| GET | `/v1/brands/:id/sources` | List knowledge sources | admin, team_member, viewer |
| GET | `/v1/brands/:id/profile` | Get brand profile | admin, team_member, viewer |
| POST | `/v1/brands/:id/profile` | Submit profile (manual path) | admin, team_member |
| PATCH | `/v1/brands/:id/profile` | Edit profile (only when PENDING_REVIEW) | admin, team_member |
| POST | `/v1/brands/:id/approve` | Lock profile and mark READY | admin |
| POST | `/v1/brands/:id/integrations/wordpress` | Configure WP connection | admin, team_member |
| POST | `/v1/brands/:id/integrations/:provider/test` | Test connection | admin, team_member |
| GET | `/v1/brands/:id/integrations` | List integrations | admin, team_member, viewer |
| DELETE | `/v1/brands/:id/integrations/:provider` | Remove integration | admin |
| POST | `/v1/uploads` | Get presigned upload URL | admin, team_member |
| GET | `/v1/jobs/:id` | Get job status | admin, team_member, viewer |

### 7.3 Endpoint Details

#### 7.3.1 POST /v1/brands

Create a new brand. The choice of `dna_source` determines what happens next:

- `dna_source = "crawl"` enqueues the onboarding pipeline (crawl → extract → ingest)
- `dna_source = "manual"` creates the brand in `DRAFT` and waits for `POST /v1/brands/:id/profile`

**Request:**
```json
{
  "name": "Acme Corp",
  "website_url": "https://acme.com",         // required if dna_source=crawl
  "dna_source": "crawl",                      // "crawl" | "manual"
  "manual_hints": {                           // optional, used by extractor as context
    "target_audience_notes": "...",
    "tone_notes": "...",
    "key_differentiators": "...",
    "topics_to_cover": ["..."],
    "topics_to_avoid": ["..."]
  },
  "uploaded_source_ids": ["uuid", "..."]      // optional, references prior uploads
}
```

**Response (201):**
```json
{
  "brand_id": "uuid",
  "status": "DRAFT",
  "dna_source": "crawl",
  "job_id": "uuid"                             // null for manual path
}
```

**Side effects:**
- Insert `brands` row
- Insert `brand_knowledge_sources` rows for `manual_hints` (as `manual_form_field` source) and `uploaded_source_ids`
- For `crawl` path: insert `jobs` row with `job_type=brand.onboard`, transition brand to `CRAWLING`, enqueue worker
- Insert `audit_logs` row: `action=brand.created`

#### 7.3.2 GET /v1/brands/:id

Returns brand summary. Does not include the profile JSON (use `/profile` for that).

**Response (200):**
```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "website_url": "https://acme.com",
  "dna_source": "crawl",
  "status": "PENDING_REVIEW",
  "failure_reason": null,
  "created_by": "uuid",
  "created_at": "2026-05-27T10:00:00Z",
  "updated_at": "2026-05-27T10:12:00Z",
  "channel_readiness": {
    "wordpress": "active",
    "shopify": null,
    "webflow": null,
    "custom_api": null
  },
  "active_job": {
    "id": "uuid",
    "status": "RUNNING",
    "stage": "EXTRACTING",
    "progress": { "pages_crawled": 8 }
  }
}
```

#### 7.3.3 DELETE /v1/brands/:id

Hard-delete a brand. This is the **reject** action.

**Side effects, in order:**
1. Clear Pinecone namespace for this `brand_id`
2. Delete from S3: any files under the brand's storage prefix (uploaded docs)
3. Delete brand row (cascade removes profile, sources, chunks, integrations, tokens, jobs)
4. Insert `audit_logs` row: `action=brand.deleted` with full snapshot in metadata

**Response (204):** no body

**Failure:** if Pinecone cleanup fails, the API returns 500 and **does not delete the Postgres row**. Manual ops intervention required. This prevents orphaned vectors.

#### 7.3.4 POST /v1/brands/:id/sources

Add a knowledge source post-creation. Only allowed when `brand.status IN ('DRAFT', 'PENDING_REVIEW')`. Adding a source in `PENDING_REVIEW` triggers a Pinecone ingest job for that source only (does **not** re-run extraction).

**Request (multipart or JSON):**
```json
{
  "source_type": "manual_text",                // 'manual_text' | 'uploaded_doc'
  "title": "Brand guidelines PDF",
  "storage_key": "uploads/abc.pdf",            // for uploaded_doc
  "raw_text": "Long-form text content...",     // for manual_text
  "metadata": { "any": "extra info" }
}
```

**Response (201):**
```json
{
  "source_id": "uuid",
  "ingest_job_id": "uuid"
}
```

#### 7.3.5 POST /v1/brands/:id/profile (manual path)

Submit a complete brand profile for the manual path. Only allowed when `brand.dna_source = 'manual'` AND `brand.status = 'DRAFT'`.

**Request:** Full `BrandProfileContent` JSON shape from Section 6.3.

**Response (201):** Returns the created profile in `BrandProfileFull` shape.

**Side effects:**
- Insert `brand_profiles` row with `generation_source=manual`, `prompt_version=null`, `extraction_model=null`, `raw_extraction=null`
- For each non-empty long-form text field (e.g. `tone_rules`, `unique_angle`), insert a `brand_knowledge_sources` row of type `manual_form_field`
- Enqueue a Pinecone ingest job for the sources
- Transition brand: `DRAFT → INGESTING → PENDING_REVIEW` (or directly to `PENDING_REVIEW` after async ingest completes)
- Audit log: `action=brand.profile_submitted_manual`

#### 7.3.6 PATCH /v1/brands/:id/profile

Edit the profile fields. **Only allowed when brand.status = 'PENDING_REVIEW'.** Returns 409 otherwise.

**Request:** Partial `BrandProfileContent` or `OperationalConfig` shape. Any field omitted is left unchanged.

**Response (200):** Updated full profile.

**Side effects:**
- Update `brand_profiles` row
- Audit log: `action=brand.profile_edited` with diff in metadata

#### 7.3.7 POST /v1/brands/:id/approve

Lock the profile and transition to `READY`. **Only allowed when brand.status = 'PENDING_REVIEW'.**

**Preconditions checked server-side:**
- Profile exists and passes schema validation
- If `publish_adapter != 'none'`, the corresponding `integration_accounts` row must exist and be `active`
- Operational fields required for the chosen `publish_adapter` must be populated (e.g. for `wordpress`, `placid_template_id` and `image_output_bucket` should be set if blog images are intended — warn but don't block)

**Response (200):**
```json
{
  "brand_id": "uuid",
  "status": "READY",
  "locked_at": "2026-05-27T11:00:00Z",
  "locked_by": "uuid"
}
```

**Side effects:**
- Set `brand_profiles.locked=true, locked_at=now(), locked_by=user_id`
- Transition brand to `READY`
- Audit log: `action=brand.approved`

#### 7.3.8 POST /v1/brands/:id/integrations/wordpress

Configure WordPress connection. Stores config and tests connection.

**Request:**
```json
{
  "site_url": "https://blog.acme.com",
  "username": "acme-publisher",
  "application_password": "abcd efgh ijkl mnop qrst uvwx",
  "default_status": "draft",                   // 'draft' | 'publish'
  "default_categories": [12, 14],              // WP category IDs, optional
  "default_author_id": null                    // WP user ID, optional
}
```

**Response (201):**
```json
{
  "integration_account_id": "uuid",
  "status": "active",
  "tested_at": "2026-05-27T10:30:00Z",
  "site_info": {                               // returned from test call
    "name": "Acme Blog",
    "url": "https://blog.acme.com",
    "user_display_name": "Acme Publisher"
  }
}
```

**Side effects:**
- Test connection (see Section 13.4)
- On success: upsert `integration_accounts` row with `provider=wordpress, status=active`, encrypt credentials into `integration_tokens`
- On failure: upsert with `status=failed, last_error=...`, return 422 with error details
- Audit log: `action=integration.wordpress.configured`

#### 7.3.9 GET /v1/jobs/:id

**Response (200):**
```json
{
  "id": "uuid",
  "brand_id": "uuid",
  "job_type": "brand.onboard",
  "status": "RUNNING",
  "stage": "EXTRACTING",
  "progress": {
    "pages_discovered": 12,
    "pages_crawled": 8,
    "extraction_attempted": true
  },
  "attempt_count": 1,
  "max_attempts": 3,
  "started_at": "2026-05-27T10:01:00Z",
  "finished_at": null,
  "error_message": null
}
```

#### 7.3.10 POST /v1/uploads

Get a presigned URL for direct upload to S3-compatible storage.

**Request:**
```json
{
  "filename": "brand-guidelines.pdf",
  "content_type": "application/pdf",
  "size_bytes": 2400000
}
```

**Response (200):**
```json
{
  "upload_url": "https://...",
  "storage_key": "uploads/2026/05/uuid-brand-guidelines.pdf",
  "expires_at": "2026-05-27T10:15:00Z"
}
```

The client uploads to `upload_url` directly. Subsequent calls reference the `storage_key`.

---

## 8. Brand DNA — Crawl Path

### 8.1 High-Level Flow

```
POST /v1/brands (dna_source=crawl)
        │
        ▼
  Brand created (DRAFT)
        │
        ▼
  Job enqueued (brand.onboard)
        │
        ▼
  Worker picks up
        │
        ├─► Stage: CRAWLING
        │       └─► Discover URLs
        │       └─► Render each page (Playwright)
        │       └─► Extract content (trafilatura)
        │       └─► Insert brand_knowledge_sources rows
        │
        ├─► Stage: EXTRACTING
        │       └─► Assemble inputs (sources + manual_hints)
        │       └─► Render prompt
        │       └─► Call LLM via OpenRouter
        │       └─► Validate JSON against schema
        │       └─► Retry once on validation failure
        │       └─► Insert brand_profiles row
        │
        ├─► Stage: INGESTING
        │       └─► Chunk normalized text
        │       └─► Generate embeddings
        │       └─► Upsert to Pinecone (namespace = brand_id)
        │       └─► Insert brand_knowledge_chunks rows
        │
        └─► Transition brand to PENDING_REVIEW
```

### 8.2 Crawler — Page Discovery Algorithm

**Goal:** Identify up to 12 URLs to fetch, ranked by likely brand-signal value.

```python
def discover_urls(seed_url: str, max_urls: int = 12) -> list[str]:
    """
    Returns up to max_urls deduplicated URLs from the same registrable domain.
    """
    urls = []

    # Step 1: Always include the homepage
    homepage = canonicalize(seed_url)
    urls.append(homepage)

    # Step 2: Try sitemap discovery
    sitemap_urls = fetch_sitemap_urls(seed_url)  # tries /sitemap.xml, /sitemap_index.xml, robots.txt
    if sitemap_urls:
        ranked = rank_by_path_keywords(sitemap_urls)
        urls.extend([u for u in ranked if u != homepage][:max_urls - 1])

    # Step 3: If sitemap didn't fill the quota, fall back to homepage link analysis
    if len(urls) < max_urls:
        homepage_html = fetch_static(seed_url)  # quick fetch, no JS
        links = extract_same_domain_links(homepage_html, base=seed_url)
        ranked = rank_by_path_keywords(links)
        for link in ranked:
            if link not in urls:
                urls.append(link)
            if len(urls) >= max_urls:
                break

    # Step 4: Identify blog index, pull latest 3 posts
    blog_index = find_blog_index(urls)
    if blog_index:
        recent_posts = extract_recent_posts(blog_index, limit=3)
        for post_url in recent_posts:
            if post_url not in urls:
                urls.append(post_url)

    return urls[:max_urls]


def rank_by_path_keywords(urls: list[str]) -> list[str]:
    """
    Score each URL by path keywords; return sorted high-to-low.
    """
    KEYWORD_SCORES = {
        'about': 10, 'team': 8, 'company': 8,
        'services': 9, 'products': 9, 'solutions': 9,
        'features': 7,
        'pricing': 6,
        'contact': 5,
        'blog': 6, 'insights': 6, 'resources': 6, 'articles': 6,
        'case-study': 7, 'case-studies': 7, 'customers': 7,
        'faq': 5,
        'careers': 2, 'jobs': 2,         # low value for brand DNA
        'privacy': 0, 'terms': 0, 'legal': 0,
    }

    def score(url: str) -> int:
        path = urlparse(url).path.lower()
        return sum(v for k, v in KEYWORD_SCORES.items() if k in path)

    return sorted(set(urls), key=score, reverse=True)
```

**Politeness rules:**

- 1 second delay between requests to the same host
- User-Agent: `100xAI-Crawler/1.0 (+https://100xai.example/bot)` — set in env as `CRAWLER_USER_AGENT`
- Respect `robots.txt` for non-homepage URLs (homepage is always fetched)
- Per-page hard timeout: 20 seconds (navigation + load)

### 8.3 Crawler — Per-Page Extraction

```python
async def fetch_and_extract(url: str) -> PageExtraction:
    """
    Fetches a URL with Playwright and extracts structured content.
    Returns None if extraction fails.
    """
    async with playwright_browser() as browser:
        page = await browser.new_page(user_agent=CRAWLER_USER_AGENT)
        try:
            await page.goto(url, wait_until='networkidle', timeout=20000)
        except TimeoutError:
            # Fall back to domcontentloaded if networkidle times out
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            except Exception:
                return None

        html = await page.content()

    # trafilatura for main content extraction
    main_text = trafilatura.extract(html, include_comments=False,
                                     include_tables=False, favor_recall=True)
    if not main_text or len(main_text) < 200:
        # fall back to readability-lxml if trafilatura yields too little
        main_text = readability_extract(html)

    if not main_text or len(main_text) < 200:
        return None  # not worth keeping

    # Structured metadata
    soup = BeautifulSoup(html, 'lxml')
    metadata = {
        'title': (soup.title.string if soup.title else '').strip(),
        'meta_description': get_meta(soup, 'description'),
        'og_title': get_meta(soup, 'og:title'),
        'og_description': get_meta(soup, 'og:description'),
        'h1': [h.get_text(strip=True) for h in soup.find_all('h1')][:3],
        'h2': [h.get_text(strip=True) for h in soup.find_all('h2')][:10],
        'outbound_links': extract_outbound_links(soup, url),
        'word_count': len(main_text.split()),
    }

    return PageExtraction(
        url=url,
        raw_text=main_text,
        normalized_text=normalize_whitespace(main_text),
        metadata=metadata,
        word_count=metadata['word_count'],
    )
```

### 8.4 Crawler — Persistence

For each successful extraction:

```python
brand_knowledge_sources.insert(
    brand_id=brand_id,
    source_type='crawled_page',
    title=metadata['title'] or extraction.url,
    url=extraction.url,
    raw_text=extraction.raw_text,
    normalized_text=extraction.normalized_text,
    metadata=extraction.metadata,
    word_count=extraction.word_count,
    fetched_at=now(),
    purge_at=now() + timedelta(days=14),
)
```

### 8.5 Crawler — Failure Handling

| Condition | Behavior |
|---|---|
| Homepage fetch fails | Mark crawl job FAILED with reason. Brand → FAILED. Team must investigate. |
| Homepage succeeds, 0 other pages | Proceed to extraction with just homepage. Flag in `job.progress.partial_crawl=true`. |
| Homepage succeeds, some pages fail | Proceed with what succeeded. Log failures in `job.progress.failed_urls`. |
| All pages timeout | Treat as homepage-only success if homepage extracted; FAILED otherwise. |
| Robots disallowed for a URL | Skip silently; log in `job.progress.robots_skipped`. |

**Always proceed if at least one page was extracted with ≥200 chars of normalized text.** The extraction step is responsible for handling thin input gracefully.

### 8.6 Crawler — Idempotency

If a `brand.crawl` job is re-run (e.g. after a worker restart), it should:

1. Delete existing `brand_knowledge_sources` of type `crawled_page` for this brand
2. Re-discover and re-crawl

This is safe because the brand is in `CRAWLING` state (not yet reviewed).

---

## 9. Brand DNA — Manual Path

### 9.1 High-Level Flow

```
POST /v1/brands (dna_source=manual)
        │
        ▼
  Brand created (DRAFT)
        │
        │  [Team fills profile form in admin panel]
        │
        ▼
POST /v1/brands/:id/profile (with full BrandProfileContent)
        │
        ▼
  brand_profiles row inserted (generation_source=manual)
        │
        │  Form long-text fields become knowledge sources:
        │  • tone_rules → manual_form_field source
        │  • unique_angle → manual_form_field source
        │  • each audience_personas[i] → manual_form_field source
        │  • each proof_points[i] → manual_form_field source
        │  • messaging_guardrails (joined) → manual_form_field source
        │
        ▼
  brand_knowledge_sources rows inserted
        │
        ▼
  Ingest job enqueued
        │
        ▼
  Stage: INGESTING
        │
        ▼
  Brand → PENDING_REVIEW
```

### 9.2 What Gets Ingested for Manual Path

Knowledge sources for manual path come from:

1. **Long-form profile fields** (auto-converted to sources on profile submit):
   - Each `audience_personas[]` entry becomes one source
   - `tone_rules` becomes one source
   - `unique_angle` becomes one source
   - Each `proof_points[]` entry becomes one source
   - Joined `messaging_guardrails[]` becomes one source if non-empty

2. **Uploaded documents** (if any were attached via `uploaded_source_ids` in create call or `POST /sources` after)

3. **Additional manual text** (added post-creation via `POST /sources`)

If the team uploads nothing and provides only minimal profile fields, the Pinecone namespace will be small. That's expected — the brand profile JSON is the primary signal for downstream prompts; vector retrieval is supplementary.

### 9.3 Why Manual Path Still Ingests

**Confirmed decision: manual path ingests to Pinecone.**

Rationale: downstream pipelines (blog generation, LinkedIn content) use RAG to retrieve brand-relevant snippets when generating content. If a brand has no vectors, those retrieval calls return empty, which makes those prompts thinner. For brands with substantial manual input or uploads, the vectors meaningfully improve generation quality. For brands with minimal input, the empty result is harmless.

Treating both paths identically (always ingest) keeps the downstream code path uniform — no `if dna_source == 'manual'` branching in the generation pipelines.

### 9.4 Manual Path Source Materialization

```python
def materialize_manual_sources(brand_id: UUID, profile: BrandProfileContent):
    sources = []

    # tone_rules
    sources.append(KnowledgeSource(
        brand_id=brand_id,
        source_type='manual_form_field',
        title='Tone Rules',
        normalized_text=profile.tone_rules,
        metadata={'field': 'tone_rules'},
    ))

    # unique_angle
    sources.append(KnowledgeSource(
        brand_id=brand_id,
        source_type='manual_form_field',
        title='Unique Angle',
        normalized_text=profile.unique_angle,
        metadata={'field': 'unique_angle'},
    ))

    # one_liner — short but worth indexing
    sources.append(KnowledgeSource(
        brand_id=brand_id,
        source_type='manual_form_field',
        title='One-Liner',
        normalized_text=profile.one_liner,
        metadata={'field': 'one_liner'},
    ))

    # audience_personas
    for i, persona in enumerate(profile.audience_personas):
        if len(persona) >= 20:  # only meaningfully long ones
            sources.append(KnowledgeSource(
                brand_id=brand_id,
                source_type='manual_form_field',
                title=f'Audience Persona {i+1}',
                normalized_text=persona,
                metadata={'field': 'audience_personas', 'index': i},
            ))

    # proof_points
    for i, proof in enumerate(profile.proof_points):
        if len(proof) >= 20:
            sources.append(KnowledgeSource(
                brand_id=brand_id,
                source_type='manual_form_field',
                title=f'Proof Point {i+1}',
                normalized_text=proof,
                metadata={'field': 'proof_points', 'index': i},
            ))

    # messaging_guardrails (joined)
    if profile.messaging_guardrails:
        joined = '\n'.join(f'- {g}' for g in profile.messaging_guardrails)
        sources.append(KnowledgeSource(
            brand_id=brand_id,
            source_type='manual_form_field',
            title='Messaging Guardrails',
            normalized_text=joined,
            metadata={'field': 'messaging_guardrails'},
        ))

    return sources
```

### 9.5 Hybrid Use Case

If a brand starts in crawl path but the team later adds manual sources (via `POST /sources` during `PENDING_REVIEW`), the `brand_profiles.generation_source` should be updated to `hybrid`. This is metadata only — the downstream pipelines do not branch on this field.

---

## 10. Extraction Worker

The extraction worker runs only on the crawl path. Its job: turn the collected `brand_knowledge_sources` into a validated `brand_profiles` row.

### 10.1 Worker Lifecycle

```python
def run_extraction_job(job_id: UUID):
    job = jobs.fetch(job_id)
    brand = brands.fetch(job.brand_id)

    # 1. Update job stage
    jobs.update(job_id, stage='EXTRACTING', status='RUNNING')
    brands.update(brand.id, status='EXTRACTING')

    try:
        # 2. Assemble input
        sources = brand_knowledge_sources.list(brand_id=brand.id)
        manual_hints = job.input_payload.get('manual_hints', {})

        input_blob = assemble_extraction_input(sources, manual_hints, brand.website_url)

        # 3. Render prompt
        prompt = render_prompt('brand_dna/v1', input_blob)

        # 4. Call LLM
        raw_response = llm.call(
            model=settings.EXTRACTION_MODEL,    # e.g. 'anthropic/claude-3-5-sonnet'
            prompt=prompt,
            response_format='json',
            max_tokens=4000,
        )

        # 5. Parse and validate
        parsed = safe_json_parse(raw_response)
        validation_errors = validate_schema(parsed, BRAND_PROFILE_SCHEMA)

        if validation_errors:
            # 6. Single retry with feedback
            retry_prompt = render_prompt('brand_dna/v1_retry', {
                **input_blob,
                'previous_response': raw_response,
                'validation_errors': validation_errors,
            })
            raw_response = llm.call(model=settings.EXTRACTION_MODEL,
                                     prompt=retry_prompt, response_format='json',
                                     max_tokens=4000)
            parsed = safe_json_parse(raw_response)
            validation_errors = validate_schema(parsed, BRAND_PROFILE_SCHEMA)
            if validation_errors:
                raise ExtractionValidationError(validation_errors)

        # 7. Persist profile
        brand_profiles.insert(
            brand_id=brand.id,
            **parsed,
            generation_source='crawl',
            prompt_version='v1',
            extraction_model=settings.EXTRACTION_MODEL,
            raw_extraction=parsed,
            # Operational fields default to nulls/empties; team fills in PENDING_REVIEW
        )

        # 8. Advance brand
        brands.update(brand.id, status='INGESTING')

        # 9. Mark this stage done; trigger ingest stage
        jobs.update(job_id, stage='INGESTING')
        enqueue('brand.ingest', brand_id=brand.id, parent_job_id=job_id)

    except Exception as e:
        handle_failure(job, brand, e)
```

### 10.2 Input Assembly

```python
def assemble_extraction_input(sources, manual_hints, website_url):
    """
    Produces a single text blob the LLM sees, structured into labeled sections.
    Token budget cap: 60,000 input tokens.
    """
    sections = []

    # 1. Manual hints first (highest signal)
    if manual_hints:
        sections.append({
            'label': 'TEAM NOTES FROM DISCOVERY CALL',
            'content': format_manual_hints(manual_hints),
        })

    # 2. Homepage (always included if present)
    homepage = next((s for s in sources if is_homepage(s.url, website_url)), None)
    if homepage:
        sections.append({
            'label': f'HOMEPAGE — {homepage.url}',
            'content': truncate(homepage.normalized_text, 8000),
        })

    # 3. About / company / services pages
    priority_pages = filter_by_path_keywords(sources, ['about', 'services',
                                                       'products', 'company'])
    for p in priority_pages[:4]:
        if p == homepage:
            continue
        sections.append({
            'label': f'PAGE — {p.metadata.get("title") or p.url}',
            'content': truncate(p.normalized_text, 4000),
        })

    # 4. Blog/insights pages — tail-truncate if over budget
    blog_pages = filter_by_path_keywords(sources, ['blog', 'insights',
                                                    'articles', 'resources'])
    remaining_budget = 60000 - sum(token_count(s['content']) for s in sections)
    for p in blog_pages:
        budget_for_this = min(3000, remaining_budget // max(1, len(blog_pages)))
        if budget_for_this < 500:
            break
        sections.append({
            'label': f'BLOG — {p.metadata.get("title") or p.url}',
            'content': truncate(p.normalized_text, budget_for_this),
        })
        remaining_budget -= token_count(p.normalized_text)

    return {
        'website_url': website_url,
        'sections': sections,
    }
```

### 10.3 Prompt — Brand DNA Extraction v1

Save as `backend/prompts/brand_dna/v1/extraction.txt`. Use `{{placeholder}}` syntax. Render with a simple templating function.

```
You are an expert brand strategist analyzing a company's web presence to
produce a structured brand profile for use in AI-driven content generation.

You will be given:
1. Optional notes from the team's discovery call with the client
2. Extracted text from several pages of the client's website

Your task: produce a single JSON object matching the BrandProfile schema below.
Return ONLY the JSON object — no preamble, no markdown fences, no explanation.

═══════════════════════════════════════════════════════════════
SCHEMA — your output must match exactly:

{
  "name": string (the brand/company name),
  "site_url": string (the canonical URL provided),
  "one_liner": string (10-500 chars; one sentence describing what the company does),
  "industry": string or null (high-level industry classification),
  "allowed_topics": string[] (at least 1; topics this brand should write about),
  "disallowed_topics": string[] (topics this brand should avoid),
  "audience_personas": string[] (at least 1; each describes a target reader),
  "tone_rules": string (at least 10 chars; describe the brand's voice rules),
  "banned_phrases": string[] (cliché AI phrases this brand avoids),
  "unique_angle": string (at least 5 chars; the brand's differentiator),
  "ctas": string[] (at least 1; approved calls-to-action for this brand),
  "proof_points": string[] (stats, social proof, credentials),
  "messaging_guardrails": string[] (high-level messaging rules),
  "compliance_keywords": string[] (keywords requiring extra care),
  "image_subject_hints": string or null (what the brand's images depict),
  "image_palette": string or null (color description),
  "visual_direction": string or null (overall visual style)
}

═══════════════════════════════════════════════════════════════
RULES:

- "banned_phrases" should include AI clichés such as "delve", "navigate",
  "unlock", "harness", "in today's fast-paced world", and any phrases that
  clash with the inferred brand tone. Aim for 8-15 entries.
- "allowed_topics" should be 5-12 concrete topic areas this brand has authority
  to write about. Be specific (e.g. "ATS keyword optimization" not "careers").
- "audience_personas" should be specific personas, not demographics. Example:
  "mid-career professionals switching into tech roles" — not "ages 25-40".
- "tone_rules" must be plain English, prescriptive, 2-4 sentences. Example:
  "Empathetic, practical, confidence-building. Not corporate. Use concrete
  numbers and examples. Avoid hype words."
- "unique_angle" should capture what differentiates this brand from competitors.
- "ctas" should be 3-6 short, actionable phrases pulled from or inferred from
  the site (e.g. "Start a free scan", "Try the AI optimizer").
- If a field cannot be inferred and is required, use a reasonable default
  based on the brand. Never return null for required fields.
- If a field is optional and cannot be inferred, return null or [].

═══════════════════════════════════════════════════════════════
INPUT:

Website URL: {{website_url}}

{{#each sections}}
─── {{label}} ───
{{content}}

{{/each}}

═══════════════════════════════════════════════════════════════
Return the JSON object now.
```

### 10.4 Prompt — Retry on Validation Failure

Save as `backend/prompts/brand_dna/v1/retry.txt`:

```
Your previous response did not validate against the schema.

Validation errors:
{{#each validation_errors}}
- {{this}}
{{/each}}

Your previous response:
{{previous_response}}

═══════════════════════════════════════════════════════════════

Read the errors carefully. Produce a corrected JSON object matching the
schema exactly. Return ONLY the JSON — no commentary.

Same input applies:

Website URL: {{website_url}}

{{#each sections}}
─── {{label}} ───
{{content}}

{{/each}}
```

### 10.5 Safe JSON Parse

```python
def safe_json_parse(raw: str) -> dict:
    """
    Strip common LLM wrappers and parse JSON.
    Raises JSONDecodeError if unparseable.
    """
    s = raw.strip()
    # Strip markdown code fences
    if s.startswith('```'):
        s = s.split('\n', 1)[1] if '\n' in s else s
        if s.endswith('```'):
            s = s[:-3]
        s = s.strip()
        if s.startswith('json\n'):
            s = s[5:]
    return json.loads(s)
```

### 10.6 LLM Provider Abstraction

```python
# backend/app/services/llm.py
from typing import Literal
import httpx

class LLMService:
    def __init__(self, api_key: str, base_url: str = 'https://openrouter.ai/api/v1'):
        self.api_key = api_key
        self.base_url = base_url

    async def call(
        self,
        model: str,
        prompt: str,
        response_format: Literal['text', 'json'] = 'text',
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """
        Single-shot LLM call. Returns the assistant's text content.
        Raises LLMError on non-2xx or empty content.
        """
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }
        if response_format == 'json':
            payload['response_format'] = {'type': 'json_object'}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': settings.APP_URL,
                    'X-Title': '100xAI Brand DNA Extractor',
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            if not content:
                raise LLMError('Empty content from LLM')
            return content
```

**Default model:** `anthropic/claude-3-5-sonnet` (set via env `EXTRACTION_MODEL`).

**Fallback model:** `openai/gpt-4o` — configured via env `EXTRACTION_MODEL_FALLBACK`. Only invoked if the primary model returns 5xx errors three times.

---

## 11. Pinecone Ingestion

### 11.1 Index Setup (One-Time)

A single Pinecone index is used for the entire platform.

| Setting | Value |
|---|---|
| Index name | `100xai-brand-knowledge` (configurable via env) |
| Dimension | 1536 |
| Metric | cosine |
| Pod / serverless | serverless |
| Cloud / region | configured at infra setup |

**Namespace strategy:** one namespace per brand, namespace value = `brand_id` (as string). This isolates brands cleanly and makes deletion a single API call.

### 11.2 Chunking

```python
def chunk_text(text: str,
               target_tokens: int = 800,
               overlap_tokens: int = 100) -> list[str]:
    """
    Splits text into chunks of ~target_tokens with ~overlap_tokens overlap.
    Splits on paragraph boundaries first, then sentence boundaries.
    Uses tiktoken for token counting.
    """
    encoder = tiktoken.encoding_for_model('text-embedding-3-small')

    # Split by paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(encoder.encode(para))

        if para_tokens > target_tokens:
            # Single paragraph is too large; split by sentence
            sentences = split_sentences(para)
            for sent in sentences:
                sent_tokens = len(encoder.encode(sent))
                if current_tokens + sent_tokens > target_tokens and current:
                    chunks.append(' '.join(current))
                    # Start new chunk with overlap
                    current = current[-overlap_count(current, encoder, overlap_tokens):]
                    current_tokens = sum(len(encoder.encode(c)) for c in current)
                current.append(sent)
                current_tokens += sent_tokens
        else:
            if current_tokens + para_tokens > target_tokens and current:
                chunks.append('\n\n'.join(current))
                current = current[-1:] if overlap_tokens > 0 else []
                current_tokens = sum(len(encoder.encode(c)) for c in current)
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append('\n\n'.join(current) if isinstance(current[0], str) else ' '.join(current))

    return [c for c in chunks if len(c) > 50]  # discard trivially small chunks
```

### 11.3 Embedding

```python
async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.
    OpenAI allows up to 2048 inputs per call; we batch at 100 for safety.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            'https://api.openai.com/v1/embeddings',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
            json={
                'model': 'text-embedding-3-small',
                'input': texts,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return [item['embedding'] for item in data['data']]
```

### 11.4 Upsert Flow

```python
async def ingest_brand_knowledge(brand_id: UUID):
    """
    Idempotent: deletes existing chunks for the brand and re-ingests.
    """
    namespace = str(brand_id)

    # 1. Clean slate (for idempotency)
    await pinecone_index.delete(delete_all=True, namespace=namespace)
    brand_knowledge_chunks.delete_by_brand(brand_id)

    # 2. Iterate sources
    sources = brand_knowledge_sources.list(brand_id=brand_id)
    all_chunks = []  # collected for batched upsert

    for source in sources:
        text = source.normalized_text
        if not text or len(text) < 50:
            continue
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            all_chunks.append({
                'brand_id': brand_id,
                'source_id': source.id,
                'chunk_index': idx,
                'text': chunk,
                'token_count': count_tokens(chunk),
                'vector_id': f'{brand_id}:{source.id}:{idx}',
                'metadata': {
                    'brand_id': str(brand_id),
                    'source_id': str(source.id),
                    'source_type': source.source_type,
                    'source_url': source.url,
                    'chunk_index': idx,
                },
            })

    # 3. Embed in batches of 100
    for batch in batched(all_chunks, 100):
        embeddings = await embed_batch([c['text'] for c in batch])
        vectors = [
            {
                'id': c['vector_id'],
                'values': emb,
                'metadata': {**c['metadata'], 'text': c['text'][:1000]},  # truncated
            }
            for c, emb in zip(batch, embeddings)
        ]
        await pinecone_index.upsert(vectors=vectors, namespace=namespace)

    # 4. Persist Postgres chunks (mirror)
    brand_knowledge_chunks.bulk_insert([
        BrandKnowledgeChunk(
            brand_id=c['brand_id'],
            source_id=c['source_id'],
            chunk_index=c['chunk_index'],
            text=c['text'],
            token_count=c['token_count'],
            vector_id=c['vector_id'],
            embedding_model='text-embedding-3-small',
            namespace=namespace,
        )
        for c in all_chunks
    ])
```

### 11.5 Query Pattern (for downstream use, documented here for reference)

```python
async def query_brand_knowledge(brand_id: UUID, query: str, top_k: int = 5):
    """
    Used by downstream content generation pipelines.
    """
    query_embedding = (await embed_batch([query]))[0]
    results = await pinecone_index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=str(brand_id),
        include_metadata=True,
    )
    return results.matches
```

### 11.6 Delete Path

```python
async def delete_brand_knowledge(brand_id: UUID):
    """
    Idempotent. Safe to call even if namespace doesn't exist.
    """
    namespace = str(brand_id)
    try:
        await pinecone_index.delete(delete_all=True, namespace=namespace)
    except PineconeNotFoundError:
        pass  # namespace didn't exist; that's fine
    # Postgres chunks are removed by FK cascade when brand is deleted
```

---

## 12. Integration Framework

### 12.1 Provider Interface

All publishing integrations conform to a single interface, regardless of provider. The interface is used both for setup/testing (during onboarding) and for publishing (in the blog pipeline — separate spec).

```python
# backend/app/integrations/base.py
from abc import ABC, abstractmethod

class IntegrationProvider(ABC):
    """
    Base class for all integration providers.
    Each concrete provider implements connection setup, testing, and publishing.
    """
    provider_name: str  # 'wordpress', 'shopify', etc.

    @abstractmethod
    async def validate_config(self, config: dict) -> ValidationResult:
        """Validate the config shape (no network call)."""
        pass

    @abstractmethod
    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        """Make a real call to verify credentials. Returns site info on success."""
        pass

    @abstractmethod
    async def publish(self, config: dict, credentials: dict, payload: PublishPayload) -> PublishResult:
        """Publish content. Used by blog pipeline; defined here for completeness."""
        pass

    @abstractmethod
    async def revoke(self, config: dict, credentials: dict) -> None:
        """Clean up any remote state on disconnect (no-op for most providers)."""
        pass
```

### 12.2 Provider Registry

```python
# backend/app/integrations/registry.py
PROVIDERS: dict[str, type[IntegrationProvider]] = {
    'wordpress': WordPressProvider,
    'shopify': ShopifyProviderStub,       # raises NotImplementedError on publish
    'webflow': WebflowProviderStub,
    'custom_api': CustomAPIProviderStub,
}

def get_provider(name: str) -> IntegrationProvider:
    if name not in PROVIDERS:
        raise UnknownProviderError(name)
    return PROVIDERS[name]()
```

### 12.3 Credential Encryption

```python
# backend/app/services/encryption.py
from cryptography.fernet import Fernet
import json

class TokenEncryptor:
    """
    Symmetric encryption for integration credentials.
    Key is loaded from env (TOKEN_ENCRYPTION_KEY) — must be a 32-byte URL-safe
    base64 string. Generate once with: Fernet.generate_key()
    """
    def __init__(self, key_b64: str, key_id: str = 'v1'):
        self.cipher = Fernet(key_b64.encode())
        self.key_id = key_id

    def encrypt(self, payload: dict) -> tuple[bytes, str]:
        plaintext = json.dumps(payload, separators=(',', ':')).encode()
        ciphertext = self.cipher.encrypt(plaintext)
        return ciphertext, self.key_id

    def decrypt(self, ciphertext: bytes, key_id: str) -> dict:
        if key_id != self.key_id:
            raise UnknownKeyVersionError(key_id)
        plaintext = self.cipher.decrypt(ciphertext)
        return json.loads(plaintext)
```

**Key rotation:** when the encryption key is rotated, the `encryption_key_id` field lets the app retain old encryptors for migration. Not implementing rotation for June 10; the field exists to enable it later without schema changes.

### 12.4 Storage Pattern

```python
async def save_integration(
    brand_id: UUID, provider: str,
    config: dict, credentials: dict, user_id: UUID,
) -> IntegrationAccount:
    # 1. Validate
    p = get_provider(provider)
    validation = await p.validate_config(config)
    if not validation.ok:
        raise ValidationError(validation.errors)

    # 2. Test
    test_result = await p.test_connection(config, credentials)
    if not test_result.ok:
        # Persist a "failed" record so the team can see the error
        account = integration_accounts.upsert(
            brand_id=brand_id, provider=provider,
            status='failed', last_error=test_result.error,
            last_tested_at=now(), created_by=user_id,
        )
        raise ConnectionTestFailedError(test_result.error)

    # 3. Encrypt credentials
    ciphertext, key_id = encryptor.encrypt(credentials)

    # 4. Persist
    account = integration_accounts.upsert(
        brand_id=brand_id, provider=provider,
        status='active', config=config,
        last_tested_at=now(), last_error=None,
        display_label=test_result.site_info.get('name'),
        created_by=user_id,
    )
    integration_tokens.upsert(
        integration_account_id=account.id,
        encrypted_payload=ciphertext,
        encryption_key_id=key_id,
    )

    # 5. Audit
    audit_logs.insert(
        action=f'integration.{provider}.configured',
        brand_id=brand_id, user_id=user_id,
        resource_id=account.id,
        metadata={'site_info': test_result.site_info},
    )

    return account
```

### 12.5 Brand Delete — Integration Cleanup

When a brand is deleted, integrations cascade-delete. For providers that support `revoke()` (e.g. revoking an OAuth token remotely), call it before the Postgres delete:

```python
async def delete_brand(brand_id: UUID, user_id: UUID):
    # 1. Revoke external integrations where applicable
    accounts = integration_accounts.list(brand_id=brand_id)
    for acc in accounts:
        try:
            p = get_provider(acc.provider)
            creds = decrypt_credentials(acc.id)
            await p.revoke(acc.config, creds)
        except Exception as e:
            logger.warning(f'Revoke failed for {acc.provider}: {e}')
            # Continue — local cleanup is more important than remote

    # 2. Clear Pinecone
    await delete_brand_knowledge(brand_id)

    # 3. Delete S3 objects
    s3.delete_prefix(f'uploads/brands/{brand_id}/')

    # 4. Hard-delete brand (cascades to all child rows)
    brand_snapshot = brands.fetch(brand_id).dict()
    brands.delete(brand_id)

    # 5. Audit
    audit_logs.insert(
        action='brand.deleted',
        user_id=user_id,
        brand_id=None,           # cascade SET NULL applies
        metadata={'snapshot': brand_snapshot},
    )
```

---

## 13. WordPress Integration (First Connector)

### 13.1 Why WordPress First

Per plan.md §3.2, June 10 requires one production CMS connector. WordPress is chosen because:

- Largest install base among small/medium content sites
- Built-in REST API since WP 4.7 (no plugin required)
- Application Passwords (since WP 5.6) provide simple, secure auth without OAuth complexity
- Wide range of post fields exposed natively (categories, tags, featured image, status, etc.)

### 13.2 Auth Method

**Application Passwords** (recommended and supported):

1. Client (or team via client's WP admin) generates an Application Password from WP user profile
2. Password format: `xxxx xxxx xxxx xxxx xxxx xxxx` (6 groups of 4 chars, spaces preserved or stripped)
3. Used with HTTP Basic Auth: `Authorization: Basic base64(username:application_password)`

**Why not OAuth:** WordPress OAuth requires a plugin (e.g. WP OAuth Server) or relies on WordPress.com infrastructure. Application Passwords work on every self-hosted WP from 5.6+ without setup.

### 13.3 Config Shape

Stored in `integration_accounts.config`:

```json
{
  "site_url": "https://blog.acme.com",
  "default_status": "draft",
  "default_categories": [12, 14],
  "default_tags": [],
  "default_author_id": null,
  "site_info": {                   // populated from successful test call
    "name": "Acme Blog",
    "description": "...",
    "url": "https://blog.acme.com"
  }
}
```

Stored in `integration_tokens.encrypted_payload` (encrypted):

```json
{
  "username": "acme-publisher",
  "application_password": "abcd efgh ijkl mnop qrst uvwx"
}
```

### 13.4 Connection Test

```python
class WordPressProvider(IntegrationProvider):
    provider_name = 'wordpress'

    async def test_connection(self, config: dict, credentials: dict) -> TestResult:
        site_url = config['site_url'].rstrip('/')
        auth = (credentials['username'], credentials['application_password'])

        async with httpx.AsyncClient(timeout=15, auth=auth) as client:
            # 1. Verify REST API is reachable
            try:
                resp = await client.get(f'{site_url}/wp-json/')
                if resp.status_code != 200:
                    return TestResult(ok=False,
                                       error=f'REST API not reachable (HTTP {resp.status_code})')
                site_info = resp.json()
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f'Network error: {e}')

            # 2. Verify auth works by hitting /users/me
            try:
                resp = await client.get(f'{site_url}/wp-json/wp/v2/users/me')
                if resp.status_code == 401:
                    return TestResult(ok=False, error='Authentication failed — check username and application password')
                if resp.status_code != 200:
                    return TestResult(ok=False, error=f'Auth check failed (HTTP {resp.status_code})')
                user_info = resp.json()
            except httpx.RequestError as e:
                return TestResult(ok=False, error=f'Network error during auth: {e}')

            # 3. Verify write capability
            caps = user_info.get('capabilities', {})
            if not (caps.get('publish_posts') or caps.get('edit_posts')):
                return TestResult(ok=False,
                                   error='User lacks publish/edit capability for posts')

            return TestResult(
                ok=True,
                site_info={
                    'name': site_info.get('name', ''),
                    'description': site_info.get('description', ''),
                    'url': site_info.get('url', site_url),
                    'user_display_name': user_info.get('name', ''),
                    'user_capabilities': list(caps.keys()),
                },
            )
```

### 13.5 Publish (Documented for Reference; Implemented with Blog Pipeline)

```python
async def publish(self, config: dict, credentials: dict, payload: PublishPayload):
    site_url = config['site_url'].rstrip('/')
    auth = (credentials['username'], credentials['application_password'])

    # 1. Upload featured image if present
    featured_media_id = None
    if payload.featured_image_url:
        media = await self._upload_media(site_url, auth, payload.featured_image_url)
        featured_media_id = media['id']

    # 2. Create post
    post_data = {
        'title': payload.title,
        'slug': payload.slug,
        'content': payload.merged_html,
        'excerpt': payload.meta_description,
        'status': config.get('default_status', 'draft'),
        'categories': config.get('default_categories', []),
        'tags': payload.tags or config.get('default_tags', []),
    }
    if featured_media_id:
        post_data['featured_media'] = featured_media_id
    if config.get('default_author_id'):
        post_data['author'] = config['default_author_id']
    # Meta description via Yoast/etc. is not exposed by core REST API;
    # use ACF or plugin-specific fields if needed (out of scope here).

    async with httpx.AsyncClient(timeout=30, auth=auth) as client:
        resp = await client.post(f'{site_url}/wp-json/wp/v2/posts', json=post_data)
        resp.raise_for_status()
        post = resp.json()

    return PublishResult(
        external_id=str(post['id']),
        public_url=post['link'],
        published_at=parse_iso(post['date_gmt']),
        raw_response=post,
    )
```

### 13.6 Stub Providers (Shopify / Webflow / Custom)

Each stub implements `validate_config` and `test_connection` to return `NotImplementedError` with a clear message, ensuring the API path is wired but publish calls fail loudly. Adapter shape exists so the data model and API surface don't need migration when these are implemented later.

```python
class ShopifyProviderStub(IntegrationProvider):
    provider_name = 'shopify'

    async def validate_config(self, config: dict):
        return ValidationResult(ok=False, errors=['Shopify integration not yet implemented'])

    async def test_connection(self, config: dict, credentials: dict):
        return TestResult(ok=False, error='Shopify integration not yet implemented')

    async def publish(self, config, credentials, payload):
        raise NotImplementedError('Shopify publish not yet implemented')

    async def revoke(self, config, credentials):
        pass
```

---

## 14. Admin Panel

### 14.1 Routes (Next.js App Router)

| Path | Purpose |
|---|---|
| `/login` | JWT login (admin/team members only) |
| `/brands` | Brand list |
| `/brands/new` | Create brand (step 1: name + path choice) |
| `/brands/:id` | Brand detail (status + tabs) |
| `/brands/:id/dna` | Brand DNA review/edit (when PENDING_REVIEW) |
| `/brands/:id/dna/manual` | Manual DNA form (when dna_source=manual & status=DRAFT) |
| `/brands/:id/sources` | Knowledge sources list + add |
| `/brands/:id/integrations` | Integration list |
| `/brands/:id/integrations/wordpress` | WP setup form |
| `/brands/:id/operational` | Operational fields form (Placid, bucket, etc.) |
| `/brands/:id/audit` | Audit log for this brand |
| `/jobs/:id` | Job detail (mainly used for polling/debug) |

### 14.2 Component Inventory

Minimum components to build:

- `BrandList` — table with name, status badge, dna_source, created date, action menu
- `BrandStatusBadge` — color-coded status (gray DRAFT, blue RUNNING states, amber PENDING_REVIEW, green READY, red FAILED)
- `CreateBrandForm` — multi-field form with dna_source radio
- `BrandDetailLayout` — tabs (Overview / DNA / Sources / Integrations / Operational / Audit) + status header
- `BrandDNAReviewForm` — structured form per profile schema field, with field grouping (Identity / Topics / Voice / CTAs / Visual)
- `BrandDNAManualForm` — same shape as review form but pre-filled with empty values
- `IntegrationCard` — provider name, status, last tested, action buttons (configure / test / disconnect)
- `WordPressSetupForm` — site URL, username, app password, default status, categories
- `OperationalConfigForm` — Placid template ID, bucket, defaults, publish adapter selector
- `SourcesList` — knowledge sources with type icon, title, word count, fetched_at
- `AddSourceModal` — paste text / upload doc
- `JobProgressIndicator` — polls `/v1/jobs/:id`, shows stage labels
- `AuditLogTable` — chronological actions for a brand
- `ApproveAndLockButton` — guarded by preconditions, shows checklist before allowing approval
- `RejectBrandButton` — confirmation modal with warnings about hard delete

### 14.3 UI States

Each form/page needs explicit handling for:

- Loading (initial fetch)
- Empty (no data yet)
- Error (fetch failed)
- Success
- Submitting (button disabled, spinner)

### 14.4 Data Fetching

- Use Server Components for initial render where possible
- Client Components for mutations and polling
- React Query (or SWR) for cache + polling
- Polling interval for job status: 3 seconds while job is RUNNING; stop when status changes

### 14.5 Approve-and-Lock Preconditions UI

Before the Approve button is enabled, show a checklist:

```
☑ Brand profile fields are complete (required fields filled)
☑ At least one knowledge source ingested  ← skip check if 0 sources is acceptable
☐ WordPress integration connected (required if publish_adapter=wordpress)
☐ Placid template ID set
☐ Image output bucket set
☐ Default location set
☐ Default language set
```

Items 3-6 are warnings, not blockers, unless `publish_adapter != 'none'`.

The Approve button is disabled until all blockers are satisfied. Warnings are shown but don't prevent approval — the team may approve a brand for LinkedIn-only use without CMS integration.

---

## 15. Job and Worker Framework

### 15.1 Queue Choice

**RQ** (Redis Queue). Rationale: simpler than Celery, sufficient for the throughput we need (tens to low hundreds of jobs per day during normal ops), easier to operate.

### 15.2 Worker Process

A single worker process consumes from the queue. Multiple worker processes can be started for parallelism; jobs are independent (one brand's job doesn't depend on another's).

```python
# worker/main.py
from rq import Worker, Queue, Connection
import redis

if __name__ == '__main__':
    redis_conn = redis.from_url(settings.REDIS_URL)
    with Connection(redis_conn):
        worker = Worker([Queue('onboarding'), Queue('default')])
        worker.work()
```

### 15.3 Job Enqueue Helper

```python
# backend/app/services/jobs.py
from rq import Queue
import redis

queue = Queue('onboarding', connection=redis.from_url(settings.REDIS_URL))

def enqueue_brand_onboarding(brand_id: UUID, manual_hints: dict = None) -> UUID:
    # 1. Insert job row
    job_row = jobs.insert(
        brand_id=brand_id,
        job_type='brand.onboard',
        status='NEW',
        input_payload={'manual_hints': manual_hints or {}},
    )

    # 2. Enqueue in Redis
    queue.enqueue(
        'worker.tasks.run_onboarding_pipeline',
        job_row.id,
        job_timeout='30m',
        result_ttl=86400,
    )

    return job_row.id
```

### 15.4 Worker Task Wrapper

```python
# worker/tasks.py
def run_onboarding_pipeline(job_id: str):
    """
    Top-level worker function. Wraps the pipeline with status updates and retry.
    """
    job = jobs.fetch(job_id)
    if job.status != 'NEW':
        logger.warning(f'Job {job_id} not in NEW status; skipping')
        return

    jobs.update(job_id, status='RUNNING', started_at=now(),
                 attempt_count=job.attempt_count + 1)

    try:
        run_crawl_stage(job_id)
        run_extract_stage(job_id)
        run_ingest_stage(job_id)
        jobs.update(job_id, status='SUCCEEDED', finished_at=now())
        brands.update(job.brand_id, status='PENDING_REVIEW')
    except RecoverableError as e:
        if job.attempt_count < job.max_attempts:
            jobs.update(job_id, status='NEW', error_message=str(e))
            # Re-enqueue with backoff
            queue.enqueue_in(timedelta(minutes=2 ** job.attempt_count),
                             'worker.tasks.run_onboarding_pipeline', job_id)
        else:
            jobs.update(job_id, status='FAILED', error_message=str(e), finished_at=now())
            brands.update(job.brand_id, status='FAILED', failure_reason=str(e))
    except UnrecoverableError as e:
        jobs.update(job_id, status='FAILED', error_message=str(e), finished_at=now())
        brands.update(job.brand_id, status='FAILED', failure_reason=str(e))
```

### 15.5 Error Classification

```python
class RecoverableError(Exception):
    """Transient errors — retry will likely succeed (network blip, rate limit)."""
    pass

class UnrecoverableError(Exception):
    """Permanent errors — retrying won't help (invalid URL, malformed response)."""
    pass

# Examples:
# - httpx.TimeoutException → RecoverableError
# - 5xx from LLM provider → RecoverableError
# - 4xx from LLM provider → UnrecoverableError (config issue)
# - JSON validation failure after retry → UnrecoverableError
# - Homepage unreachable → UnrecoverableError (manual intervention needed)
```

### 15.6 Manual Path Has No Pipeline Job

The manual path does **not** create a `brand.onboard` job. It does create a `brand.ingest` job (smaller scope) when the profile is submitted. The state transitions for manual path are direct, not async:

```
POST /v1/brands (manual) → brand=DRAFT, no job
POST /v1/brands/:id/profile → insert profile, materialize sources, brand=INGESTING, enqueue ingest job
ingest job runs → brand=PENDING_REVIEW
```

---

## 16. Prompts and Prompt Governance

### 16.1 Folder Structure

```
backend/
└── prompts/
    └── brand_dna/
        ├── v1/
        │   ├── extraction.txt          # main extraction prompt
        │   ├── retry.txt               # retry with validation feedback
        │   └── system_notes.md         # human-readable notes on the version
        └── v2/                         # future
```

### 16.2 Templating

Use a simple Jinja2-based templating (Python). All prompts are loaded at app startup and cached.

```python
# backend/app/services/prompts.py
from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader('backend/prompts'),
    autoescape=False,  # we want raw text
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_prompt(template_path: str, context: dict) -> str:
    """
    template_path is relative to backend/prompts/, e.g. 'brand_dna/v1/extraction.txt'
    """
    template = env.get_template(template_path)
    return template.render(**context)
```

### 16.3 Version Discipline

- Every prompt file in `v1/` is frozen. Edits go in `v2/`.
- The `brand_profiles.prompt_version` field records which version produced a given profile.
- When bumping versions, do not silently change behavior — document the change in `system_notes.md`.

### 16.4 Initial Prompt Set

**v1/extraction.txt** — the main brand DNA extraction prompt (full text in Section 10.3).

**v1/retry.txt** — single-shot retry on validation failure (full text in Section 10.4).

**v1/system_notes.md** — human-readable changelog:

```markdown
# Brand DNA Prompts — v1

**Status:** Active
**Created:** 2026-05-27
**Author:** [engineering]

## Purpose
First working version of the brand DNA extraction prompt set.
Sufficient for the Phase 1 milestone; expected to be refined with
input from Priyam's persona doc when available.

## Known limitations
- May produce generic "tone_rules" for brands with thin website content.
  Mitigation: team review-and-edit during PENDING_REVIEW.
- "banned_phrases" tends to default to a stock list of AI clichés;
  brand-specific aversions may not be inferred without strong signal.
- "compliance_keywords" is rarely populated unless the input mentions
  regulated industries (medical, legal, financial).
```

---

## 17. Security and Multi-Tenancy

### 17.1 Auth

- JWT-based authentication. Tokens carry `user_id`, `org_id`, `role`.
- All API endpoints require a valid JWT. Token expiry: 24 hours; refresh tokens optional in this scope.
- Frontend stores token in HttpOnly cookie.

### 17.2 Role-Based Access

| Role | Permissions |
|---|---|
| `admin` | All operations including delete brand, configure integrations, approve, hard delete |
| `team_member` | Create brand, edit profile (in PENDING_REVIEW), configure integrations, but cannot approve or delete |
| `viewer` | Read-only across all brands in the org |

Approval and deletion are admin-only because they're terminal actions.

### 17.3 Tenant Scoping

Every query that reads or writes brand-scoped data **must** filter by `org_id`. The `org_id` is extracted from the JWT and applied as a query filter — never trust client-provided `org_id` values.

**Pattern:**

```python
# backend/app/repositories/brands.py
def get_brand(brand_id: UUID, org_id: UUID) -> Brand:
    brand = db.query(Brand).filter(
        Brand.id == brand_id,
        Brand.org_id == org_id,         # ← tenant scope, NEVER omit
    ).first()
    if not brand:
        raise NotFoundError()
    return brand
```

A missing tenant filter is a high-severity bug. Add a linter rule or code review checklist item.

### 17.4 Encryption at Rest

- Integration credentials: Fernet encryption (Section 12.3)
- All other PII (emails, names): Postgres column-level — not required for Phase 1, but documented as a future enhancement
- TLS for all external API calls (httpx defaults are correct)

### 17.5 Secret Management

- All API keys live in environment variables loaded via Pydantic Settings
- `.env` file is gitignored; `.env.example` documents required keys without values
- Never log secrets. The logging configuration scrubs known secret patterns.

### 17.6 Audit Logging — What Gets Logged

| Action | Trigger |
|---|---|
| `brand.created` | POST /v1/brands |
| `brand.profile_submitted_manual` | POST /v1/brands/:id/profile |
| `brand.profile_edited` | PATCH /v1/brands/:id/profile |
| `brand.approved` | POST /v1/brands/:id/approve |
| `brand.deleted` | DELETE /v1/brands/:id |
| `brand.failed` | Worker writes failure |
| `brand.source_added` | POST /v1/brands/:id/sources |
| `integration.{provider}.configured` | POST /v1/brands/:id/integrations/... |
| `integration.{provider}.test_failed` | Connection test failure |
| `integration.{provider}.removed` | DELETE /v1/brands/:id/integrations/:provider |

Each audit log row captures `user_id`, `brand_id`, action, and a structured `metadata` JSON with relevant context (e.g. diff for edits, error details for failures).

### 17.7 Rate Limiting

- LLM calls: handled by OpenRouter; no app-side limiting needed
- Pinecone: batched upserts at 100 vectors per call; built-in throttling not required at this scale
- Outbound HTTP from crawler: 1s per-host delay (Section 8.2)
- API endpoints: no rate limiting in Phase 1 (internal use only)

---

## 18. Folder Structure

### 18.1 Backend

```
backend/
├── alembic/
│   ├── versions/
│   │   └── 20260527_0001_onboarding_subsystem.py
│   ├── env.py
│   └── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entrypoint
│   ├── config.py                        # Pydantic Settings
│   ├── db.py                            # SQLAlchemy engine + session
│   ├── deps.py                          # FastAPI dependencies (auth, db, etc.)
│   ├── auth/
│   │   ├── jwt.py
│   │   └── rbac.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── brands.py
│   │   ├── brand_profile.py
│   │   ├── brand_sources.py
│   │   ├── integrations.py
│   │   ├── jobs.py
│   │   └── uploads.py
│   ├── models/                          # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── brand.py
│   │   ├── brand_profile.py
│   │   ├── brand_knowledge_source.py
│   │   ├── brand_knowledge_chunk.py
│   │   ├── integration_account.py
│   │   ├── integration_token.py
│   │   ├── job.py
│   │   └── audit_log.py
│   ├── schemas/                         # Pydantic models + JSON schemas
│   │   ├── brand.py
│   │   ├── brand_profile.py
│   │   ├── brand_profile_v1.json
│   │   ├── integration.py
│   │   └── job.py
│   ├── repositories/                    # DB access layer
│   │   ├── brands.py
│   │   ├── profiles.py
│   │   ├── sources.py
│   │   ├── chunks.py
│   │   ├── integrations.py
│   │   ├── jobs.py
│   │   └── audit_logs.py
│   ├── services/                        # business logic
│   │   ├── brand_service.py
│   │   ├── crawler.py
│   │   ├── extractor.py
│   │   ├── ingestion.py
│   │   ├── pinecone_client.py
│   │   ├── llm.py
│   │   ├── prompts.py
│   │   ├── encryption.py
│   │   └── s3.py
│   ├── integrations/                    # external provider adapters
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── wordpress.py
│   │   └── stubs.py
│   └── utils/
│       ├── html.py                      # HTML cleaning, link extraction
│       ├── text.py                      # normalization, tokenization, chunking
│       └── urls.py                      # canonicalization, ranking
├── prompts/
│   └── brand_dna/
│       └── v1/
│           ├── extraction.txt
│           ├── retry.txt
│           └── system_notes.md
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── sample_brand_site/           # fake HTML for crawler tests
│   │   └── sample_profile_outputs/      # LLM output samples for review
│   ├── unit/
│   │   ├── test_url_ranking.py
│   │   ├── test_chunking.py
│   │   ├── test_schema_validation.py
│   │   └── test_encryption.py
│   └── integration/
│       ├── test_onboarding_crawl.py
│       ├── test_onboarding_manual.py
│       └── test_wordpress_integration.py
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### 18.2 Worker

```
worker/
├── main.py                              # RQ worker entrypoint
├── tasks/
│   ├── __init__.py
│   ├── onboarding.py                    # run_onboarding_pipeline + stages
│   ├── ingest.py                        # run_ingest_only (manual path)
│   └── purge.py                         # nightly raw_text purge
└── requirements.txt
```

### 18.3 Frontend

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                         # redirect → /brands
│   ├── login/
│   │   └── page.tsx
│   ├── brands/
│   │   ├── page.tsx                     # brand list
│   │   ├── new/
│   │   │   └── page.tsx                 # create brand
│   │   └── [id]/
│   │       ├── layout.tsx               # detail tabs
│   │       ├── page.tsx                 # overview
│   │       ├── dna/
│   │       │   ├── page.tsx             # review/edit
│   │       │   └── manual/
│   │       │       └── page.tsx         # manual form
│   │       ├── sources/
│   │       │   └── page.tsx
│   │       ├── integrations/
│   │       │   ├── page.tsx
│   │       │   └── wordpress/
│   │       │       └── page.tsx
│   │       ├── operational/
│   │       │   └── page.tsx
│   │       └── audit/
│   │           └── page.tsx
│   └── jobs/
│       └── [id]/
│           └── page.tsx
├── components/
│   ├── ui/                              # ShadCN base components
│   ├── brand/
│   │   ├── BrandList.tsx
│   │   ├── BrandStatusBadge.tsx
│   │   ├── CreateBrandForm.tsx
│   │   ├── BrandDNAReviewForm.tsx
│   │   ├── BrandDNAManualForm.tsx
│   │   ├── ApproveAndLockButton.tsx
│   │   └── RejectBrandButton.tsx
│   ├── integrations/
│   │   ├── IntegrationCard.tsx
│   │   ├── WordPressSetupForm.tsx
│   │   └── OperationalConfigForm.tsx
│   ├── sources/
│   │   ├── SourcesList.tsx
│   │   └── AddSourceModal.tsx
│   ├── jobs/
│   │   └── JobProgressIndicator.tsx
│   └── audit/
│       └── AuditLogTable.tsx
├── lib/
│   ├── api/                             # API client (Axios/fetch wrappers)
│   ├── auth.ts
│   └── types.ts                         # generated from OpenAPI or hand-written
├── package.json
└── .env.example
```

---

## 19. Environment Configuration

### 19.1 Backend `.env.example`

```bash
# Application
APP_ENV=development
APP_URL=http://localhost:8000
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/centxai

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=replace-with-a-strong-random-string-at-least-32-chars
JWT_EXPIRY_HOURS=24

# Token encryption (generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
TOKEN_ENCRYPTION_KEY=
TOKEN_ENCRYPTION_KEY_ID=v1

# LLM
OPENROUTER_API_KEY=
EXTRACTION_MODEL=anthropic/claude-3-5-sonnet
EXTRACTION_MODEL_FALLBACK=openai/gpt-4o
EXTRACTION_MAX_TOKENS=4000
EXTRACTION_TEMPERATURE=0.3

# Embeddings
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Pinecone
PINECONE_API_KEY=
PINECONE_INDEX_NAME=100xai-brand-knowledge
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Object storage (S3-compatible)
S3_ENDPOINT_URL=                              # leave empty for AWS S3
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=100xai-uploads
S3_REGION=us-east-1

# Crawler
CRAWLER_USER_AGENT=100xAI-Crawler/1.0 (+https://100xai.example/bot)
CRAWLER_MAX_PAGES=12
CRAWLER_PAGE_TIMEOUT_SEC=20
CRAWLER_HOST_DELAY_SEC=1
```

### 19.2 Frontend `.env.example`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 19.3 Pre-Development Setup Checklist

Before starting Day 1 implementation:

- [ ] Postgres 15+ instance accessible (local Docker is fine)
- [ ] Redis 7+ instance accessible
- [ ] Pinecone account created, index `100xai-brand-knowledge` created with dimension 1536, metric cosine
- [ ] OpenRouter API key
- [ ] OpenAI API key (for embeddings — separate from extraction LLM)
- [ ] S3-compatible storage (MinIO for local dev, real S3 for staging)
- [ ] `TOKEN_ENCRYPTION_KEY` generated and stored
- [ ] `JWT_SECRET` generated
- [ ] Playwright installed: `playwright install chromium`

---

## 20. Testing Strategy

### 20.1 Test Layers

**Unit tests** (`tests/unit/`) — pure functions, no I/O:

- URL canonicalization and ranking
- Path-keyword scoring
- Text chunking
- JSON schema validation
- Safe JSON parsing
- Token encryption round-trip
- State machine transitions

**Integration tests** (`tests/integration/`) — exercise full flows with fakes:

- End-to-end crawl path: fixture HTML files → discovery → extraction → profile → ingest (with mocked LLM and Pinecone)
- End-to-end manual path: profile submission → ingest (with mocked Pinecone)
- WordPress integration: connection test against a recorded HTTP fixture (use `respx` or `vcrpy`)
- Schema validation failure → retry path

**Manual smoke tests** — operated by the team:

- Onboard 3 real client websites of different stack types (WordPress site, Shopify storefront, JS-heavy SPA)
- Onboard 1 manual-only client (no website)
- Verify Pinecone has correct vector counts and queries return reasonable results
- Verify WordPress publish flow against a sandbox WP site

### 20.2 Test Fixtures

Save sample crawled sites in `tests/fixtures/sample_brand_site/`:

```
sample_brand_site/
├── index.html
├── about.html
├── services.html
├── blog/
│   ├── index.html
│   ├── post-1.html
│   ├── post-2.html
│   └── post-3.html
└── README.md  (describes the fictional brand the fixtures simulate)
```

Serve via a local Python HTTP server for integration tests:
`python -m http.server 9876 --directory tests/fixtures/sample_brand_site`

### 20.3 LLM Mocking in Tests

Use a fake LLM service that returns canned JSON for known inputs:

```python
# tests/fakes/llm.py
class FakeLLMService:
    def __init__(self, canned_responses: dict[str, str]):
        self.canned = canned_responses

    async def call(self, model, prompt, **kwargs) -> str:
        # Match on a hash of the prompt or a keyword
        for key, response in self.canned.items():
            if key in prompt:
                return response
        return json.dumps(DEFAULT_FAKE_PROFILE)
```

### 20.4 Pinecone Mocking in Tests

Use an in-memory fake:

```python
class FakePineconeIndex:
    def __init__(self):
        self._namespaces = {}

    async def upsert(self, vectors, namespace):
        self._namespaces.setdefault(namespace, {})
        for v in vectors:
            self._namespaces[namespace][v['id']] = v

    async def delete(self, delete_all, namespace):
        self._namespaces.pop(namespace, None)

    async def query(self, vector, top_k, namespace, **kwargs):
        # return arbitrary top_k from the namespace; no real similarity
        ns = self._namespaces.get(namespace, {})
        items = list(ns.values())[:top_k]
        return {'matches': items}
```

### 20.5 Coverage Targets

Don't chase 100% coverage. Targets:

- Unit test coverage on `utils/`, `services/text.py`, `services/encryption.py`: 90%+
- Integration test for each happy path of crawl, manual, WordPress
- One integration test per failure mode (LLM error, validation fail, WP auth fail)

---

## 21. Implementation Plan (Day-by-Day)

These are working days, not calendar days. Each day produces a mergeable PR.

### Day 1 — Foundation

**Deliverables:**
- Alembic initialized
- Migration `20260527_0001_onboarding_subsystem.py` with all tables from Section 4.2
- SQLAlchemy models for all tables
- Pydantic schemas matching Section 6.3
- JWT auth + RBAC middleware
- Repositories with tenant-scoped query helpers
- Basic logging configuration

**Acceptance:**
- `alembic upgrade head` runs cleanly on empty DB
- `pytest tests/unit/test_schema_validation.py` passes
- `pytest tests/unit/test_encryption.py` passes
- A test client can authenticate and call `/v1/brands` (which returns empty list)

### Day 2 — Crawler Service

**Deliverables:**
- Playwright integration (Chromium headless)
- URL discovery (sitemap + homepage link analysis)
- URL ranking by path keywords
- Per-page rendering and trafilatura extraction
- Source persistence to DB

**Acceptance:**
- `pytest tests/unit/test_url_ranking.py` passes
- Manual run: `python -m app.services.crawler https://acme-test.example` returns ≥3 extracted pages with non-empty normalized_text
- Test with local fixture server: discover and extract all sample pages

### Day 3 — Extraction Worker + Manual Path

**Deliverables:**
- LLM service abstraction (OpenRouter client)
- Prompts `v1/extraction.txt` and `v1/retry.txt` checked in
- Extractor service: input assembly, LLM call, JSON validation, single retry
- `POST /v1/brands/:id/profile` endpoint (manual path)
- Materialize manual sources from form fields

**Acceptance:**
- `pytest tests/unit/test_schema_validation.py` passes (already from Day 1)
- Integration test: fixtures → extractor → valid profile JSON written to DB
- Integration test: manual profile submit → DB row with `generation_source=manual`

### Day 4 — Pinecone Ingestion + WordPress Integration

**Deliverables:**
- Pinecone client wrapper
- Chunking algorithm with tiktoken
- Embedding service (OpenAI text-embedding-3-small)
- Ingest worker task
- WordPress provider class (validate + test_connection)
- Integration account + token storage with encryption
- `POST /v1/brands/:id/integrations/wordpress` endpoint
- Brand hard-delete service (Pinecone clear → S3 clear → DB cascade)

**Acceptance:**
- Integration test: crawl path → ingest → Pinecone namespace has N vectors
- Integration test: WordPress test_connection succeeds against fixture HTTP server (mocking WP REST responses)
- Integration test: brand delete clears Pinecone + DB + S3
- Manual smoke: configure real WordPress sandbox; connection test passes

### Day 5 — Admin Panel (Backend Wiring)

**Deliverables:**
- All API endpoints from Section 7.2 implemented and tested
- OpenAPI spec auto-generated
- Polling endpoint for jobs
- Audit log writes for all relevant actions

**Acceptance:**
- All endpoints documented in OpenAPI / Swagger UI
- Full crawl-path onboarding flow tested via HTTP requests (postman/httpx scripts)
- Audit log entries appear for every state transition

### Day 6 — Admin Panel (Frontend)

**Deliverables:**
- Next.js app scaffold with auth
- Brand list page
- Create brand page (with dna_source selection)
- Brand detail page with tabs
- DNA review/edit form
- DNA manual form
- Sources list + add source modal
- Integrations page + WordPress setup form
- Operational config form
- Approve-and-lock button with checklist
- Reject button with confirmation modal

**Acceptance:**
- A team member can complete a full onboarding (crawl path) entirely through the UI
- A team member can complete a full onboarding (manual path) entirely through the UI
- A team member can configure WordPress and see "connected" status
- A team member can approve a brand and see status flip to READY
- A team member can reject a brand and see it removed from the list

### Day 7 — Hardening, Smoke Tests, Buffer

**Deliverables:**
- Run all four smoke tests (Section 20.1)
- Document any issues found and fixes
- Performance check: onboarding completes in <5 min for typical site
- Error path UX polish (clear error messages on UI)

**Acceptance:**
- 3 real-site smoke tests pass
- 1 manual-only smoke test passes
- WP publish test against sandbox passes
- No P0 bugs open

---

## 22. Acceptance Criteria (Subsystem Complete)

The onboarding subsystem is complete when **all** of these are true:

### 22.1 Functional

- [ ] A team member can authenticate and access the admin panel
- [ ] A team member can create a brand with `dna_source=crawl`
- [ ] The crawler discovers and fetches ≥1 page from a real client website
- [ ] The extractor produces a JSON brand profile that validates against schema
- [ ] The Pinecone namespace for the brand contains vectors after ingest
- [ ] The brand transitions to `PENDING_REVIEW` automatically after ingest
- [ ] A team member can review and edit the generated profile
- [ ] A team member can create a brand with `dna_source=manual` and submit a profile via form
- [ ] The manual path also ingests sources to Pinecone
- [ ] A team member can configure a WordPress integration
- [ ] The WordPress test_connection passes against a real WP site
- [ ] An admin can approve a brand and the status changes to `READY`
- [ ] After approval, the profile is immutable (PATCH returns 409)
- [ ] An admin can hard-delete a brand and Pinecone is cleared
- [ ] All actions write to `audit_logs`

### 22.2 Quality

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No hardcoded credentials in source
- [ ] No silent failures — every error path either returns to user or writes to audit log
- [ ] Logs do not contain secrets
- [ ] All endpoints are tenant-scoped (no cross-org leakage possible)

### 22.3 Operational

- [ ] `.env.example` documents every required env var
- [ ] `alembic upgrade head` runs cleanly from empty DB
- [ ] `docker-compose up` brings the full stack online for local dev
- [ ] Worker process can be started independently and processes queued jobs
- [ ] Each successful onboarding produces:
  - 1 `brands` row
  - 1 `brand_profiles` row
  - ≥1 `brand_knowledge_sources` rows
  - ≥1 `brand_knowledge_chunks` rows (or 0 if no ingestable content)
  - 1+ `audit_logs` rows
  - Pinecone vectors in a namespace named with the brand_id

---

## 23. Decisions Log

This log records the design decisions made during specification. Each entry is dated and the rationale is captured for future reference.

### D-001 — Onboarding is internal-team only
**Date:** 2026-05-27
**Decision:** No client-facing self-serve onboarding. The internal team operates onboarding during a booked discovery call.
**Rationale:** Allows quality > speed in the extraction pipeline; team applies judgment on AI-generated profile; reduces complexity (no public form UX, no client auth scope).

### D-002 — `brand_profiles` is the ClientProfile
**Date:** 2026-05-27
**Decision:** The `brand_profiles` table is the same record as the Pillar Blog Engine's ClientProfile. One source of truth, no separate projection table.
**Rationale:** Two tables guarantee drift. Operational fields and AI-generated fields coexist cleanly in one row.

### D-003 — Two-path brand DNA (crawl + manual)
**Date:** 2026-05-27
**Decision:** Brand DNA can be constructed via crawl pipeline OR direct manual form submission. Both paths produce the same row shape.
**Rationale:** Some clients have no website; some have insufficient website content. Manual path covers both. Single output shape keeps downstream pipelines uniform.

### D-004 — Manual path also ingests to Pinecone
**Date:** 2026-05-27
**Decision:** The manual path materializes form long-text fields and uploaded docs into `brand_knowledge_sources`, then runs Pinecone ingestion.
**Rationale:** Downstream RAG retrieval works uniformly across both paths; no `if dna_source == 'manual'` branching in generation pipelines. Empty namespace is harmless.

### D-005 — No edit after lock
**Date:** 2026-05-27
**Decision:** Once a brand is `READY`, the profile is immutable. PATCH returns 409. To change anything, hard-delete and re-onboard.
**Rationale:** Matches the Pillar Blog Engine spec philosophy ("if onboarding ever needs more than the above, fix it there, not in the prompt"). Forces team to make changes that propagate cleanly to all downstream artifacts.

### D-006 — Edit allowed during `PENDING_REVIEW`
**Date:** 2026-05-27
**Decision:** During the `PENDING_REVIEW` window, team can freely edit the profile fields via PATCH. The "no edit" rule applies after lock, not before.
**Rationale:** The team uses the discovery-call context to refine AI-generated values before locking. This is fundamentally different from iterating on blog content (which is approve/reject only).

### D-007 — Hard delete on reject
**Date:** 2026-05-27
**Decision:** Rejecting a brand hard-deletes all related data (DB rows, Pinecone vectors, S3 files). No soft delete.
**Rationale:** Soft delete adds drift risk and Pinecone cost. Simpler invariant: every brand row corresponds to a live brand.

### D-008 — Pinecone namespace per brand
**Date:** 2026-05-27
**Decision:** Single Pinecone index, one namespace per brand (namespace = brand_id).
**Rationale:** Single-call deletion on brand delete. Cleaner isolation. Simpler than metadata-filter-based deletion.

### D-009 — WordPress first, others stubbed
**Date:** 2026-05-27
**Decision:** Only WordPress has a working integration UI in Phase 1. Shopify/Webflow/Custom have stub adapters that return clear errors.
**Rationale:** Per master plan §3.2, June 10 requires one production CMS connector. WordPress is highest-coverage. Adapter interface exists so adding others later is non-breaking.

### D-010 — Application Passwords for WordPress
**Date:** 2026-05-27
**Decision:** Use WordPress Application Passwords (HTTP Basic Auth) rather than OAuth.
**Rationale:** Built-in since WP 5.6. No plugin required. Simpler UX during onboarding call.

### D-011 — RQ over Celery
**Date:** 2026-05-27
**Decision:** Use RQ (Redis Queue) for job processing.
**Rationale:** Simpler operational model. Sufficient throughput for expected load. Easier to debug.

### D-012 — text-embedding-3-small
**Date:** 2026-05-27
**Decision:** Use OpenAI `text-embedding-3-small` (dimension 1536) for embeddings.
**Rationale:** Best cost/quality tradeoff. Large enough to capture nuance, small enough that Pinecone storage and query cost are minimal.

### D-013 — Channel readiness separate from brand readiness
**Date:** 2026-05-27
**Decision:** A brand can be `READY` without any integrations connected. Channel availability is tracked per `integration_accounts` row.
**Rationale:** Brand DNA is required for all pipelines; CMS integration is only required for blog publishing. LinkedIn, WhatsApp will be other independent integrations. Decoupling allows partial provisioning.

### D-014 — Hybrid generation_source for late additions
**Date:** 2026-05-27
**Decision:** If a brand starts in crawl path and later has manual sources added (during PENDING_REVIEW), set `generation_source=hybrid`.
**Rationale:** Provenance metadata; no behavior change.

### D-015 — 14-day retention on crawled raw text
**Date:** 2026-05-27
**Decision:** `raw_text` for `source_type=crawled_page` is nulled out 14 days after fetch. Normalized text persists indefinitely.
**Rationale:** Crawled content is third-party; retain only what's needed. Normalized text is sufficient for re-ingestion and audit.

---

## 24. Glossary

| Term | Definition |
|---|---|
| **Brand** | A single client tenant in the system. One client = one brand in Phase 1. |
| **Brand DNA** | The AI-extracted (or manually entered) personality, voice, audience, and content guidelines for a brand. |
| **Brand Profile** | The persisted row containing all brand DNA fields plus operational config. Same as ClientProfile. |
| **ClientProfile** | Pillar Blog Engine's term for the brand profile record. Identical to `brand_profiles` in this spec. |
| **Crawl Path** | Brand DNA construction by crawling the client's website and extracting profile via LLM. |
| **Manual Path** | Brand DNA construction by team filling out a form directly, no crawl, no extraction. |
| **DNA Source** | Field on the brand record: `crawl` or `manual`. Determines which path was used. |
| **Generation Source** | Field on the brand profile: `crawl`, `manual`, or `hybrid` (post-create source additions). |
| **Knowledge Source** | A single input artifact for a brand: crawled page, uploaded doc, manual text block. |
| **Knowledge Chunk** | A subdivision of a source's text, sized for embedding (~800 tokens). One chunk = one Pinecone vector. |
| **Integration Account** | A connection between a brand and an external provider (WordPress, etc.). Has config + encrypted credentials. |
| **Channel Readiness** | Whether a given external channel is connected for a brand. Independent of brand readiness. |
| **Brand Readiness** | Whether a brand's profile is locked (status = READY). |
| **PENDING_REVIEW** | State where team can edit the profile. Last chance before lock. |
| **READY** | Terminal success state. Profile is immutable. Brand is usable by downstream pipelines. |
| **Lock** | Set `brand_profiles.locked=true` on approval. Profile becomes immutable. |
| **Hard Reject / Hard Delete** | Permanently remove a brand and all associated data. The "restart from scratch" path. |
| **Engine Layer** | Generic, frozen code that doesn't change per client (Pillar Blog Engine terminology). |
| **Client Layer** | Per-client data — the brand profile and any uploaded sources. The thing that changes per client. |

---

**End of specification. Version 1.0 — 2026-05-27.**

Any field, endpoint, table, or behavior not specified in this document is undefined for this subsystem. Add to the Decisions Log before implementing anything that isn't here.