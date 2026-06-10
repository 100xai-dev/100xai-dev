# 100xAI Platform - Technical Handover Document

## Project Overview
100xAI is evolving from an AI blog generation platform into a **Blog Scheduling and Content Calendar Platform** with AI generation as a powerful feature. The platform focuses on automated content scheduling and publishing across multiple channels, with WordPress as the primary integration target.

## Current Architecture

### Technology Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Next.js with TypeScript
- **Database**: PostgreSQL
- **Queue System**: Redis + RQ (Redis Queue)
- **AI Models**: Anthropic Claude (primary), OpenRouter (fallback)
- **External Services**: 
  - Apify (web scraping)
  - SerpApi (SERP analysis)
  - Leonardo AI (image generation)
  - Placid (image templates)

### Core Pipelines

#### Pipeline 1: Keyword Research
- **Location**: `backend/app/services/seo_research.py::run_keyword_research`
- **Purpose**: Discovers and analyzes keywords for content strategy
- **Key Issue Fixed**: Primary keyword wasn't being saved - fixed by adding it to the keyword list (line 1052-1062)
- **Data Sources**: Apify Google Search, DataForSEO (fallback), AI filtering

#### Pipeline 2: SERP Analysis  
- **Location**: `backend/app/services/seo_research.py::run_serp_analysis`
- **Purpose**: Analyzes competitor content for identified keywords
- **Integration**: Uses SerpApi for SERP data, Apify for competitor content crawling
- **Output**: Competitor gaps, content recommendations

#### Pipeline 3: Content Generation
- **Location**: `backend/app/services/content_generation.py`
- **Purpose**: Generates complete SEO-optimized blog articles
- **Features Implemented**:
  - CEO's SEO requirements (2% main keyword density, 0.5-1% sub-keywords)
  - FAQ section generation with schema.org markup
  - Multi-track parallel content generation
  - Image generation via Leonardo AI
  - Branded templates via Placid

### Recent Bug Fixes

1. **Pipeline Integration Bug**: Pipeline 3 couldn't read Pipeline 2 SERP data
   - Fixed by updating `load_serp_analysis` to accept optional `serp_job_id` parameter
   - Added fallback to most recent SERP analyses

2. **SERP Analysis Validation Bug**: Endpoint incorrectly reported "no keywords found"
   - Fixed by simplifying keyword detection query in `backend/app/routers/brands.py`
   - Changed from complex subquery to list-based approach

3. **Blog UI Integration**: Integrated Pipeline 3 with existing blog UI
   - Updated `backend/app/routers/blogs.py` to create both BlogJob and Pipeline 3 Job
   - Added status mapping between pipeline stages and blog UI statuses

4. **Missing Primary Keyword**: Searched keywords weren't appearing in discovered list
   - Fixed by adding primary keyword to the keyword list in `run_keyword_research`
   - Primary keyword now appears with source_type "primary_search"

## Planned Architecture Changes

### From AI Generator to Scheduling Platform

#### New Database Schema (`backend/app/models/schedule.py`)
```python
BlogSchedule - Main scheduling table
├── scheduled_at (5-minute blocks)
├── recurrence_type (NONE, DAILY, WEEKLY, MONTHLY)
├── content_source (AI_GENERATED, MANUAL, IMPORTED)
├── target_channels (wordpress, shopify, etc.)
└── status (DRAFT, SCHEDULED, PUBLISHED, FAILED)

PublishingQueue - Queue management
├── scheduled_for
├── priority (1-10)
├── channel
└── retry_count

ChannelIntegration - Store OAuth/API credentials
├── channel_type
├── access_token_encrypted
├── refresh_token_encrypted
└── site_url
```

#### Publishing Integration Strategy

1. **WordPress (Primary)**
   - OAuth integration (preferred) - to be set up with clients via calls
   - REST API fallback with application passwords
   - Custom plugin option for advanced features

2. **Custom Websites**
   - Webhook integration (most flexible)
   - Custom API adapters
   - FTP/SFTP upload for legacy systems
   - RSS feed generation
   - Email delivery as fallback

3. **Scheduler Design**
   - 5-minute block precision
   - Cron job runs every 5 minutes
   - Platform owns all content (no two-way sync)
   - Auto-retry once on failure, then email user

#### Automated Onboarding Flow
```
Sign Up → Auto-detect CMS → Self-service Integration → Test Publish
                    ↓ (if stuck)
            Schedule Support Call (optional)
```

Key features:
- Platform detection using HTML/header analysis
- Dynamic integration guides based on detected platform
- Call scheduling as safety net, not requirement
- Target: 65% self-service completion rate

## Critical Files and Functions

### Backend Core Files
- `backend/app/services/seo_research.py` - All keyword research and SERP analysis
- `backend/app/services/content_generation.py` - Blog content generation with SEO optimization
- `backend/app/routers/brands.py` - Brand management and pipeline endpoints
- `backend/app/routers/blogs.py` - Blog job management (integrated with Pipeline 3)
- `backend/app/routers/schedules.py` - **NEW** Blog scheduling and calendar API endpoints
- `backend/app/services/job_dispatcher.py` - Queue management for all pipelines
- `backend/app/models/schedule.py` - **NEW** Scheduler database models
- `backend/app/schemas/schedule.py` - **NEW** Scheduler API schemas
- `backend/app/models/` - Database models

### Frontend Key Components
- Blog management UI with polling system
- Calendar view (to be implemented)
- Integration wizard (to be implemented)

## Environment Configuration

### Required API Keys
```env
# AI Services
ANTHROPIC_API_KEY=           # Primary LLM
OPENROUTER_API_KEY=          # Fallback LLM

# SEO & Research  
SERPAPI_API_KEY=             # SERP analysis
DATAFORSEO_API_KEY=          # Keyword research (base64 encoded login:password)
APIFY_API_KEY=               # Web scraping

# Content Enhancement
LEONARDO_API_KEY=            # AI image generation
PLACID_API_KEY=              # Branded templates (optional)

# Vector Database
PINECONE_API_KEY=            # Knowledge storage
OPENAI_API_KEY=              # Embeddings only
```

### Model Configuration
```env
EXTRACTION_MODEL=anthropic/claude-3-5-sonnet-20241022
EXTRACTION_MODEL_FALLBACK=anthropic/claude-3-5-haiku-20241022
BLOG_MODEL=anthropic/claude-3-opus-20241022
```

## Development Workflow

### Running Locally
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Worker (in separate terminal)
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
PYTHONPATH=backend:. \
backend/venv/bin/rq worker --with-scheduler \
onboarding blog purge keyword_research serp_analysis content_generation publisher default
# NOTE: `content_generation` and `publisher` are required. Content jobs enqueue to
# `content_generation`; omitting it makes article generation silently stall.
# Scheduled auto-publish runs on `blog` (via enqueue_at, needs --with-scheduler).

# Frontend
cd frontend
npm install
npm run dev
```

### Database Migrations
```bash
# Create new migration
alembic revision -m "description"

# Apply migrations
alembic upgrade head
```

## Testing Credentials

### DataForSEO
- Currently using: `aGFyc2hAcml0emNvcnBvcmF0aW9uLmNvbTpiZmQ3NDU5MzJiYzgxNWQ1`
- This is base64 encoded login:password format

### Test Flow
1. Create brand → Triggers onboarding job
2. Run keyword research → Discovers keywords
3. Start SERP analysis → Analyzes competition
4. Generate content → Creates full blog post
5. **NEW** Create schedule → `POST /v1/schedules/` with blog_job_id
6. View calendar → `GET /v1/schedules/brands/{brand_id}/calendar`
7. Publishing automation → **⚠️ Still needs implementation**

## Scheduler Implementation Status (June 2026)

### ✅ COMPLETED - Scheduler Foundation
**Database Models** (`backend/app/models/schedule.py:43-203`)
- ✅ `BlogSchedule` - Main scheduling table with 5-minute precision
- ✅ `ScheduleTemplate` - Templates for recurring content
- ✅ `ContentCalendar` - Aggregated calendar view 
- ✅ `PublishingQueue` - Queue management for publishing tasks
- ✅ Database migration applied: `alembic/versions/20260607_0009_blog_scheduling_tables.py`

**API Endpoints** (`backend/app/routers/schedules.py:1-168`)
- ✅ `POST /v1/schedules/` - Create schedule
- ✅ `GET /v1/schedules/{id}` - Get schedule details
- ✅ `GET /v1/schedules/brands/{brand_id}/calendar` - Calendar view
- ✅ `DELETE /v1/schedules/{id}` - Delete schedule
- ✅ Schema definitions: `backend/app/schemas/schedule.py`
- ✅ Integrated with existing auth/RBAC system

**Model Relationships Fixed**
- ✅ SQLAlchemy relationship error resolved by updating `app/models/__init__.py`
- ✅ All scheduler models properly imported and relationships working
- ✅ `Brand.schedules`, `BlogJob.schedules`, `BlogDraft.schedules` relationships active

### ✅ DONE as of June 9, 2026 (see "Session Update — June 9, 2026" above)

**Step 3: Publishing Worker Tasks**
- ✅ `backend/worker/tasks/scheduler.py` exists; `publish_scheduled_blog(schedule_id)` auto-publishes a generated draft at its due time.
- ✅ Scheduling is per-schedule via RQ `enqueue_at` (no separate cron needed; worker runs `--with-scheduler`).
- ⚠️ The older `run_publishing_scheduler`/`process_publishing_queue` (PublisherFactory + `publishing_queue` table) path also exists but the calendar flow uses the simpler `publish_scheduled_blog` path.

**Step 4: WordPress Publishing**
- ✅ Publishing works via `backend/app/services/wp_publish.py::publish_blog_draft` (REST API + Application Passwords), used by both manual approve and scheduled auto-publish.
- ❌ OAuth flow not implemented (Application Passwords only, per-brand creds in encrypted token OR inline `config`).

**Step 5: Calendar UI**
- ✅ `frontend/app/brands/[id]/calendar/page.tsx` — multi-day select + per-day keyword + bulk schedule, shows scheduled chips.

### 🎯 Current Status Summary
The scheduler **foundation is complete and ready for use**. Users can:
- Create, view, and manage schedules via API
- Access calendar views for content planning
- Delete draft schedules (published ones protected)

**Missing for full automation:**
- Publishing worker to process schedules at scheduled times
- Channel adapters (WordPress, webhook, etc.) to actually publish content
- Calendar UI for easy schedule management

## Known Issues & TODOs

### Critical Path Items
1. ✅ **Publishing workers** - Done (manual approve + scheduled auto-publish via `wp_publish` / `publish_scheduled_blog`)
2. 🔶 **WordPress publishing** - Done via Application Passwords; OAuth still TODO
3. ✅ **Calendar UI components** - Done (`calendar/page.tsx` multi-day scheduling)
4. 🔶 **Webhook integration** - Test endpoint exists; scheduled publishing path is WordPress-only so far
5. ❌ **Automated onboarding wizard** - Self-service setup
6. ❌ **Phase 2: brand image reuse** - Needs object storage + image embeddings (plan: `~/.claude/plans/compressed-baking-owl.md`)
7. 🔶 **Backfill Pinecone for existing brands** - RAG works; run `backfill_all_brands` / per-brand `/reingest` to populate all brands

### Technical Debt
1. Worker timeout issues (increased to 600-900 seconds as workaround)
2. Memory optimization needed for Apify free tier
3. Pipeline status synchronization could be cleaner
4. Need better error handling in content generation

### Feature Requests
1. Recurring schedule support
2. Multi-channel cross-posting
3. Content performance analytics
4. Two-way sync with publishing platforms (not planned currently)
5. Bulk scheduling via CSV upload

## Business Context

### Platform Positioning
- **Current**: AI blog generator with scheduling features
- **Target**: "AI-Powered Content Calendar" - scheduling platform with AI generation
- **Key Differentiator**: Automated scheduling and publishing, not just generation

### Integration Philosophy
- Self-service onboarding by default
- Support calls as optional safety net
- Platform owns content management
- One-way publishing (no sync back)

### Success Metrics
- 75% onboarding completion rate
- 65% self-service setup (no call needed)  
- 95% publishing success rate
- <35 minutes to first published post

## Contact & Support

### Development Team Notes
- API rate limits: Be mindful of Apify/DataForSEO quotas
- Use `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` on macOS for RQ worker
- Pipeline 3 jobs use same ID as BlogJob for consistency
- Scheduler will run on 5-minute blocks for resource efficiency

### Architecture Decisions Made
1. **Authentication Storage**: OAuth where possible, encrypted credentials as fallback
2. **Scheduling Precision**: 5-minute blocks for good balance
3. **Content Ownership**: Platform manages everything (no two-way sync)
4. **Failure Handling**: Auto-retry once, email user, move to draft queue

---

## Session Update — June 9, 2026 (publishing, scheduling UI, Pinecone RAG)

This session took the platform from "scheduler foundation" to **working end-to-end publishing + a usable content calendar + functioning brand-knowledge RAG**. Five threads, all verified against the live local stack.

### 1. WordPress connection test failing "repeatedly" (auth plumbing)
**Symptom:** WordPress integration test failed every time, even though the credentials were valid (verified by running the provider's `test_connection` directly in the venv — `ok=True`).

**Root cause (two compounding bugs):**
- The Next.js proxy (`frontend/app/api/[...path]/route.ts`) **strips the incoming `Authorization` header** and authenticates only via the `100xai_access_token` **cookie** (set with `max-age=900` = 15 min).
- The integration/publishing pages set `Authorization: Bearer ${localStorage.getItem('token')}` — but the token is stored under **`100xai_access_token`**, not `'token'`, and they never refreshed the session. Once the 15-min cookie expired, every proxied call got `401 "missing bearer token"` → UI showed the generic "Connection test failed".

**Fixes:**
- Replaced `localStorage.getItem('token')` with `await getValidAccessToken()` (refreshes token + re-sets the cookie the proxy reads) in: `integrations/page.tsx`, `integrations/wordpress/page.tsx`, `integrations/webhook/page.tsx`, `publishing/monitor/page.tsx`.
- Consolidated the duplicate/shadowed test routes in `backend/app/routers/integrations.py` into one `POST /{provider_or_id}/test` that resolves the account **by id or provider name** and reads creds from the **encrypted token OR inline `config`** (channel-created integrations store creds in `config`, not a token). Added `_credentials_for_account()` helper. Deleted the dead mock endpoint.

> ⚠️ **Auth gotcha for the next dev:** the proxy ignores client `Authorization` headers and uses the `100xai_access_token` cookie (15-min TTL). For manual API testing, hit the backend (`:8000`) directly with `Authorization: Bearer <jwt>`; through the proxy, rely on the cookie. Always use `getValidAccessToken()` in frontend fetches, never `localStorage.getItem('token')`.

### 2. "Approve & Publish" — 422, then it didn't actually publish
- **422 on `POST .../approve-article`:** `ApproveArticleRequest` is an empty model but FastAPI still required a body; the frontend sent none. Made the param optional (`ApproveArticleRequest | None = None`) in `backend/app/routers/blogs.py`.
- **Bigger issue:** `approve_article` only set `job.status="PUBLISHED"` in the DB — **nothing ever published to WordPress** (`publishing_queue`/`blog_schedules` were empty). Wired it to actually publish via a new shared service `backend/app/services/wp_publish.py::publish_blog_draft` (resolves WP account + creds, builds `PublishPayload`, calls the WordPress provider with `status="publish"`). Verified by publishing a real post live.

### 3. Content generation jobs not running / stuck on "generating"
- **Queue mismatch:** content jobs are enqueued to the **`content_generation`** queue (`job_dispatcher.py`), but the worker command in use omitted it → jobs sat unconsumed. **The worker MUST include `content_generation`** (and `publisher`).
- **Two code crashes in `content_generation.py`** (attribute names didn't match the DB models): `comp.competitive_advantages` → `competitive_advantage`; `s.target_url` → `s.top_competitor_url`.
- **Stuck "generating" UI:** `blogs.py::get_blog_job` status map had `("FAILED", None)` but failed jobs have `stage="CONTENT"`, so a FAILED job never surfaced as FAILED and the UI polled forever. Fixed to treat `FAILED` as terminal at any stage.

### 4. Calendar scheduling workflow (new feature)
Implemented the "pick days → enter a keyword per day → generate now, auto-publish on the day" flow.
- **Frontend** `frontend/app/brands/[id]/calendar/page.tsx` — rewritten from read-only to multi-day select → scheduling modal (one keyword input per selected date + one publish time) → bulk submit. Shows scheduled posts as status chips.
- **Backend** `backend/app/routers/schedules.py` — **fixed a crash** (`db.func.extract` → date-range filter; `Session` has no `.func`). Added `POST /v1/schedules/brands/{brand_id}/bulk`: per (date, keyword) it kicks off generation immediately AND creates a `SCHEDULED` row that **auto-publishes at the chosen time** via RQ `enqueue_at` on the `blog` queue (`JobDispatcher.enqueue_publish_blog_at` → `worker/tasks/scheduler.py::publish_scheduled_blog`, which reuses `wp_publish.publish_blog_draft`).
- Product decisions (from user): one keyword per day; generate-now + auto-publish-on-day; one fixed time for all. Auto-publish currently has **no manual review step** (by design).

### 5. Pinecone brand-knowledge RAG (the "tailored to brand" goal)
**Root cause of "Pinecone isn't storing anything":** a **typo in the index name** — the index that existed was `100xai-br**na**d-knowledge`, but config pointed at `100xai-br**an**d-knowledge`, so every `upsert` 404'd and the error was **swallowed** by `onboarding_pipeline.py::_ingest_stage` (138 sources → 0 chunks). Separately, `query_brand_knowledge()` existed but was **never called**, so generation never used brand knowledge anyway.

**Implemented (Phase 1 — text RAG + DNA), all in `backend/`:**
- `app/services/ingestion.py`: `ensure_index`/`get_pinecone_index` factory (create-if-missing at correct 1536 dim); instrumented `ingest_brand_knowledge` (returns `{sources_total, chunks_built, dna_docs, vectors_upserted}`); `build_dna_chunks` embeds the BrandProfile as 6 DNA docs (Pinecone-only, no migration); fixed `query_brand_knowledge` for Pinecone SDK v9 (`.matches`, normalized dicts).
- `app/services/onboarding_pipeline.py`: `_ingest_stage` now uses the factory and **surfaces** skip/failure via `ingest_status` instead of silently returning 0 (doesn't block `PENDING_REVIEW`). Added `run_reingest_job`, `find_brands_needing_reingest`, `backfill_all_brands`.
- `app/routers/brand_sources.py`: `POST /v1/brands/{id}/sources/reingest` (idempotent backfill, no re-crawl). `JobDispatcher.enqueue_reingest` + `worker/tasks/onboarding.py::run_reingest` (onboarding queue).
- `app/services/retrieval.py`: `retrieve_brand_grounding` (graceful empty fallback). Wired into `content_generation.py` — retrieved **once per article** and injected into the **brief**, **body-section**, and **brand-value** prompts (additive; empty string = byte-identical to old prompts).
- Config: added `pinecone_cloud` / `pinecone_region` for serverless index creation.

**Verified E2E:** brand ApexNeural → 20 sources → 32 knowledge chunks + 6 DNA docs = 38 vectors; retrieval returned ~3.8k chars of real brand grounding; app boots (58 routes).

**Operational follow-ups:**
- **Restart backend + worker**; worker queue list MUST include `content_generation` and `publisher`:
  `... keyword_research onboarding serp_analysis blog content_generation publisher default purge`
- **Backfill remaining brands** (only ApexNeural has chunks so far): `backfill_all_brands(db)` or `POST /reingest` per brand.
- **Delete the orphaned misspelled Pinecone index** `100xai-brnad-knowledge`.

### Phase 2 — NOT started (planned, gated on prerequisites)
"Reuse the brand's past images for visual consistency" needs net-new infra: real object storage (`store_image_in_bucket` is currently a **stub** that returns the external URL), image capture during crawl (`screenshot_url` is always `None`), and multimodal/CLIP image embeddings (none exist; OpenAI embeddings are text-only). Plan saved at `~/.claude/plans/compressed-baking-owl.md`. Prerequisites to confirm: S3/GCS creds, image-embedding provider, reuse-vs-style-reference policy.

---

## Recent Session Summary (June 2026)

### Fixed Issues
1. **SQLAlchemy Relationship Error** - `BlogSchedule` class couldn't be found
   - **Root Cause**: Missing imports in `backend/app/models/__init__.py` 
   - **Fix**: Added imports for `BlogSchedule`, `ContentCalendar`, `PublishingQueue`, `ScheduleTemplate`
   - **Impact**: All scheduler model relationships now work correctly

2. **Scheduler Foundation Implementation**
   - **Database**: Created and applied migration for all scheduler tables
   - **API**: Built complete REST API for schedule management
   - **Testing**: Verified all endpoints working with proper authentication

### Implementation Decisions Made
1. **5-minute scheduling precision** - Balances flexibility with resource efficiency
2. **Status-based schedule protection** - Published schedules can't be deleted/edited
3. **Org-based data isolation** - All schedules scoped to user's organization
4. **Role-based access** - Admin/team_member can create, viewer can read

### Next Developer Notes
- Publishing workers need Redis job scheduling (RQ + cron)
- WordPress adapter should use OAuth flow for security
- Calendar UI should use date-picker libraries (react-datepicker)
- Consider using webhook queues for custom site publishing

---

## Session Update — June 9, 2026 (email verification, Razorpay billing, T&C)

Branch: `feat/email-verification-razorpay-terms`. Three account/monetization features added.
Migrations applied; 23 new backend tests pass; frontend typechecks clean. (Pre-existing
failures in `tests/test_brand_delete.py` and `tests/test_onboarding_worker.py` are unrelated —
confirmed present on `main`.)

### 0. Crawler dependency fix (prerequisite)
- `firecrawl-py` was declared but not installed, and the pin `>=1.5.0` allowed the
  API-incompatible v4. Pinned to `>=1.5.0,<2.0.0` (code uses the v1 `crawl_url`/`scrape_url`
  API) and installed `1.17.0` into `backend/venv`. Fixes `brand.onboard` jobs failing at
  CRAWLING with `No module named 'firecrawl'`.

### 1. Email verification (hard block at login)
- **Flow**: signup creates the account, emails a single-use link, and returns
  `SignupResponse {requires_verification: true}` with **no tokens**. Login is blocked with
  `403 {"code": "email_not_verified"}` until verified. `verify-email` marks the user verified
  and auto-logs-in. Because tokens are only issued post-verification, a valid access token
  inherently implies a verified user — no per-request check needed (`deps.get_current_user`
  only decodes the JWT).
- **Endpoints**: `POST /v1/auth/verify-email`, `POST /v1/auth/resend-verification` (generic
  response, no account enumeration).
- **Email service**: `backend/app/services/email.py` — `console` backend (logs the link, dev
  default) or `smtp` backend (stdlib `smtplib`, any provider, no new dependency). Sent via
  FastAPI `BackgroundTasks`.
- **Model**: `User.email_verified`, `email_verified_at`; new `EmailVerificationToken`
  (sha256-hashed token, expiry, single-use) in `backend/app/models/core.py`.
- **Frontend**: `app/verify-email/page.tsx`, signup→notice redirect, login catches the 403,
  `middleware.ts` PUBLIC_PATHS extended.

### 2. Razorpay recurring subscriptions
- **Plan catalog** (`backend/app/services/billing_plans.py`) — placeholder INR pricing:
  Free ₹0 (1 brand, 3 blogs/mo) · Starter ₹999 (3, 30) · Pro ₹2999 (10, 150). Edit here to
  change pricing/limits. Razorpay plan ids come from env per tier.
- **Service** (`backend/app/services/billing.py`): `create_subscription`, `cancel_subscription`,
  `verify_webhook_signature`, `handle_event` (idempotent via `webhook_events`), and
  `enforce_plan_limit` (raises **402** with a `plan_limit_reached` detail).
- **Endpoints** (`backend/app/routers/billing.py`, prefix `/v1/billing`): `GET /plans`,
  `GET /subscription`, `POST /subscribe`, `POST /cancel`, `POST /webhook` (no auth —
  signature-verified, reads raw body).
- **Enforcement wired** into `brands.py::create_brand_endpoint` (brands) and
  `content_generation.py::trigger_content_generation` (content-gen Jobs / month).
- **Models** (`backend/app/models/billing.py`): `Subscription`, `WebhookEvent`; plus
  `Organization.plan_code` (default `free`).
- **Frontend**: `app/billing/page.tsx` (Razorpay Checkout JS), nav link, 402→upgrade prompt.
- **TODO before live**: set `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET`, create Starter/Pro plans
  in the Razorpay dashboard and set `RAZORPAY_PLAN_STARTER/PRO`, register the webhook URL.

### 3. Versioned Terms & Conditions
- Required checkbox at signup (`SignupRequest.accept_terms`, validated). `User.terms_version_accepted`
  + timestamp recorded. `/me` and auth responses return `terms_acceptance_required` (true when
  the stored version ≠ `CURRENT_TERMS_VERSION`). `POST /v1/auth/accept-terms` records acceptance.
- **Frontend**: `app/terms/page.tsx` (placeholder copy), `components/TermsGuard.tsx` blocking
  modal mounted in the root layout, signup checkbox.

### Migrations & config
- `alembic/versions/20260609_0010_email_verification_and_terms.py` (verification + terms columns,
  grandfathers existing users as `email_verified=true`), `20260609_0011_billing.py` (billing tables
  + `organizations.plan_code`). Both applied.
- `razorpay>=1.4.0` added to `requirements.txt` (installed `2.0.1`).
- New env vars in `backend/.env` (see config.py): `FRONTEND_URL`, `EMAIL_BACKEND`, `SMTP_*`,
  `EMAIL_VERIFICATION_EXPIRY_HOURS`, `CURRENT_TERMS_VERSION`, `RAZORPAY_*`. Defaults to
  `EMAIL_BACKEND=console` so verification works in dev with no SMTP setup.

### Tests
- `tests/test_auth.py` rewritten for the new flow (verification-gated). New `tests/test_terms.py`,
  `tests/test_billing.py` (Razorpay client + signature mocked, webhook idempotency, 402 limits).

---

*Last updated: June 9, 2026*
*Document reflects: WordPress publishing (manual + scheduled auto-publish), calendar multi-day scheduling UI, content-generation queue/bug fixes, auth-proxy fixes, and Pinecone brand-knowledge RAG (ingestion fix + DNA embedding + retrieval wired into generation). See "Session Update — June 9, 2026" at the top of the session summaries.*