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
onboarding blog purge keyword_research serp_analysis content_generation default

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

### 🔄 IN PROGRESS - Next Implementation Steps

**Step 3: Publishing Worker Tasks** (Priority 1)
- ❌ Create `backend/worker/tasks/scheduler.py` 
- ❌ Implement cron-based 5-minute scheduler
- ❌ Add publishing queue processor
- ❌ Handle channel-specific publishing

**Step 4: WordPress Publishing Adapter** (Priority 2)
- ❌ Create `backend/app/services/publishers/wordpress.py`
- ❌ OAuth integration for WordPress sites  
- ❌ REST API publishing with authentication

**Step 5: Calendar UI Components** (Priority 3)
- ❌ Create `frontend/app/brands/[id]/calendar/page.tsx`
- ❌ Calendar view component
- ❌ Schedule creation/editing forms

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
1. ❌ **Build publishing workers** - Core automation functionality  
2. ❌ **WordPress OAuth integration** - Primary publishing target
3. ❌ **Calendar UI components** - User-friendly scheduling interface
4. ❌ **Webhook integration** - Custom site publishing
5. ❌ **Automated onboarding wizard** - Self-service setup

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

*Last updated: June 7, 2026*
*Document reflects scheduler foundation implementation and SQLAlchemy relationship fixes*