# Design: Payment-gated crawling + profile status

**Date:** 2026-06-16
**Status:** Approved (documents the approach already present in the working tree)

## Problem

A new user can sign up, add a brand, and the platform immediately starts
crawling the brand's URL — with no payment involved. Crawling and all
downstream generation features should require an active paid subscription
first. There is also no place for a user to see their payment status.

## Current state (codebase findings)

- **Crawl trigger:** `POST /v1/brands` → `create_brand_endpoint`
  (`backend/app/routers/brands.py`) → `create_brand()`
  (`backend/app/services/brand_service.py`) enqueues a `brand.onboard` crawl
  job. The only guard is `enforce_plan_limit(RESOURCE_BRANDS)`, and the **free
  plan allows 1 brand** (`backend/app/services/billing_plans.py`), so an
  unpaid org crawls for free. This is the hole.
- **Payment infra already exists:** Razorpay subscriptions (`Subscription`
  model in `backend/app/models/billing.py`), `/v1/billing/*` router, a webhook
  that promotes `org.plan_code` to the paid tier while a subscription is active
  (and reverts to `free` otherwise), a working `/billing` checkout page, and a
  plan catalog (free / starter ₹999 / pro ₹2999). New orgs default to
  `plan_code="free"` (`backend/app/models/core.py`).
- **No profile/account page** exists in the active frontend (`frontend/`).

## Decisions

1. **"Paid" = an active paid subscription** (starter or pro). Free orgs are
   locked out of crawling and generation.
2. **Gate enforced at brand creation AND all generation features**: brand
   create (crawl), keyword research, SERP analysis, content generation.
3. **New `/profile` page** showing account info + payment status. Status
   display only for now; the only action is a link to `/billing`.

## Architecture

### Backend — the subscription gate

A single chokepoint in `backend/app/services/billing.py`:

- `has_active_subscription(db, org_id) -> bool`
  - Returns `True` when `org.plan_code != DEFAULT_PLAN_CODE` ("free"). The
    webhook already promotes `plan_code` on activation, so this is the primary
    signal.
  - Fallback: the latest `Subscription` row for the org is in an active state
    (`active | authenticated | charged | completed`) with a non-free
    `plan_code`. This covers the window between checkout success and the
    webhook landing.
- `require_active_subscription(db, org_id) -> None`
  - Raises `HTTPException(402)` with detail
    `{"code": "subscription_required", "message": "..."}` when the org is not
    paid.

`402 Payment Required` is chosen over `403` to stay consistent with the
existing `plan_limit_reached` 402 response, so the frontend treats both as
billing-related.

**Wiring** — `require_active_subscription` is called **before** the existing
`enforce_plan_limit` calls (a subscription is a prerequisite for any quota
check) at four endpoints:

| Endpoint | File |
| --- | --- |
| `create_brand_endpoint` | `backend/app/routers/brands.py` |
| `start_keyword_research` | `backend/app/routers/brands.py` |
| `start_serp_analysis` | `backend/app/routers/brands.py` |
| `trigger_content_generation` | `backend/app/routers/content_generation.py` |

### Frontend — paywall UX

- **`ApiError` class** in `frontend/lib/api.ts`, carrying `status` (number) and
  optional `code` (string) parsed from the backend's
  `{detail: {code, message}}` body. `apiRequest` throws `ApiError` instead of a
  bare `Error`, so callers can branch on `err.code === "subscription_required"`
  rather than string-matching messages. Because `ApiError extends Error`, all
  existing `err instanceof Error ? err.message` handlers keep working.
- **`CreateBrandForm`** (`frontend/components/brand/create-brand-form.tsx`)
  catches `subscription_required` and renders an upgrade notice with a
  "View plans & subscribe" button linking to `/billing`, instead of a raw
  error string.

### Profile page (`/profile`)

A client component (`frontend/app/profile/page.tsx`) consistent with the
existing top-level `/billing` page:

- Account block: name, email, organization — sourced from `useAuth()`.
- Payment-status block: an **Active / Not subscribed** badge, current plan
  name, subscription status, and renewal/end date — sourced from
  `getSubscription()`.
- A "View plans & subscribe" / "Manage subscription" link to `/billing`.

Navigation: the brands layout header
(`frontend/app/brands/layout.tsx`) gains **Billing** and **Profile** links.

## Data flow

```
User submits "Create Brand"
  → POST /v1/brands
    → require_active_subscription(org)
        paid?  → enforce_plan_limit → create_brand → enqueue crawl job → 201
        unpaid → 402 {code: subscription_required}
  → frontend: 402+code → CreateBrandForm shows upgrade notice → /billing
    → Razorpay checkout → webhook activates subscription → org.plan_code = paid
  → retry Create Brand → succeeds
```

The same `require_active_subscription` precondition guards keyword research,
SERP analysis, and content generation.

## Error handling

- Backend raises `402` with a stable `code` so the UI can render a tailored
  message and CTA.
- Frontend `ApiError` preserves status + code; non-paywall errors fall through
  to the existing generic error display.
- The webhook path is unchanged; it remains the source of truth that flips
  `org.plan_code`, and `has_active_subscription` reads from it.

## Testing

- **New tests** (`backend/tests/test_billing.py`):
  - Free org → `402` with `code == "subscription_required"` on brand create.
  - Paid org (`plan_code="pro"`) → `201` on brand create.
  - `has_active_subscription` returns `True` via the `Subscription`-row
    fallback when `org.plan_code` is still free.
- **Fixture change** (`backend/tests/conftest.py`): `create_user` gains a
  `plan_code` parameter (default `"free"`, preserving existing billing tests
  that rely on the free default).
- **Updated tests** (~10): brand-creation tests in
  `tests/integration/test_onboarding_api.py`, `tests/test_queue_wiring.py`, and
  `tests/test_brand_delete.py` pass `plan_code="pro"`, because they test
  brand/crawl behavior, not the paywall.

Out of scope: `tests/test_blog_pipeline.py::test_content_brief_coerces_list_audience_and_range_word_count`
is a pre-existing, unrelated failure (fails in isolation before these changes).

## Behavior change (breaking)

Existing free-tier orgs **lose** the ability to create brands and run
generation until they subscribe. This is intended per the "pay first"
requirement, but it is a breaking change for any current free users and should
be communicated before deploy.

## Out of scope (YAGNI)

- One-time payments / Razorpay orders (we reuse subscriptions).
- Editing profile details, plan downgrades/upgrades beyond the existing
  `/billing` flow.
- Removing the `free` plan from the catalog (it stays as the unpaid/locked
  state; its `brands`/`blogs` limits simply become unreachable for creation
  since the subscription gate runs first).
