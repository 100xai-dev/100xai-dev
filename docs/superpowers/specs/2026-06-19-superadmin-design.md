# Superadmin — Design Spec

**Date:** 2026-06-19
**Branch:** `feat/email-verification-razorpay-terms`
**Status:** Approved (design); ready for implementation plan

## 1. Goal

Introduce a **platform superadmin** who can view, edit, onboard, and create
organizations, and who can "enter" any organization to operate its dashboard
exactly as that org's own admin would. The superadmin controls everything in
the app across all tenants.

Two surfaces:

1. **Superadmin dashboard landing** — a list of all organizations, with
   management actions (create/onboard, edit, manage users, suspend/delete).
2. **Enter an organization** — drill into one org and see *all* the features and
   options that org sees on their own dashboard, with full read + write access.

## 2. Background (current architecture)

- **Org-scoping is uniform.** Every route filters by `current_user.org_id`,
  which is decoded from the JWT alongside `role`
  (`backend/app/deps.py:27-35`). The `CurrentUser` dataclass is
  `(id, org_id, role)`.
- **Roles** are `viewer` / `team_member` / `admin`, ordered in
  `backend/app/auth/rbac.py:4-8`; routes gate with
  `require_role(actual, allowed)`.
- **Single org per user.** `users.org_id` is a direct NOT-NULL FK; an
  `Organization` is created at signup (`backend/app/models/core.py:20-37`).
  There is no memberships table.
- **Organization** has only `id`, `name`, `plan_code` — no status field.
- **Frontend** dashboard lives at `/brands`; the whole app is already
  org-scoped via the session in `frontend/context/AuthContext.tsx`. `role` is
  already returned to the client in `UserOut` (`backend/app/schemas/auth.py:51-59`).
- **API proxy** (`frontend/app/api/[...path]/route.ts:25-30`) forwards all
  non-hop-by-hop headers to the backend, so a custom header flows through
  automatically. Client `apiRequest` calls hit `/api...`; server components call
  the backend directly with the cookie token (`frontend/lib/api.ts:77-98`).

## 3. Chosen approach — Acting-org context

The superadmin keeps their own session. When they "enter" an org, the client
sets an acting-org cookie; every API call carries an `X-Acting-Org-Id` header. A
backend dependency — **only after verifying from the JWT that the caller is a
superadmin** — swaps the effective `org_id` to the target org. Every existing
org-scoped route and every existing dashboard page then works **unchanged**.

**Rejected alternatives:**

- **Impersonation tokens** (mint a token scoped to the target org): adds token
  lifecycle complexity (refresh/expiry/revoke-on-exit) and muddies "who am I"
  in logs.
- **Parallel `/superadmin/*` read+write API** taking an explicit `org_id`:
  duplicates the entire dashboard API. Rejected by YAGNI.

**Security boundary:** the override is honored only when the *verified JWT role*
is `superadmin`. A normal user who sets the header themselves is ignored.

## 4. Detailed design

### 4.1 Identity & provisioning

- Add `superadmin` to `ROLE_ORDER` (`backend/app/auth/rbac.py`) with the highest
  rank, and make `require_role` treat `superadmin` as satisfying **every**
  requirement — so all existing `require_role(...)` calls pass for a superadmin
  acting on an org.
- **Seeding:** a one-off script / CLI (driven by a `SUPERADMIN_EMAILS` env var)
  creates a dedicated **system organization** plus the superadmin `User`
  (`role="superadmin"`, `email_verified=True`) inside it. This keeps the
  `users.org_id` NOT-NULL FK intact with no schema change, and there is no
  public signup path that can ever mint a superadmin.
- The seed is idempotent: re-running reconciles the listed emails to superadmin
  without creating duplicates.

### 4.2 Acting-org mechanism (backend)

- New dependency `get_acting_context` (single edit point; may replace the body
  of `get_current_user`): reads the optional `X-Acting-Org-Id` header. If the
  JWT role is `superadmin` **and** the referenced org exists, return
  `CurrentUser(id=<superadmin id>, org_id=<target org>, role="superadmin")`.
  Otherwise behave exactly as today; for non-superadmins the header is ignored
  entirely.
- Because `require_role` waves `superadmin` through and `org_id` is now the
  target org, all brand / blog / schedule / integration / billing reads **and**
  writes operate on the target org with zero per-route changes.
- If `X-Acting-Org-Id` references a non-existent org, return 404.

### 4.3 Superadmin-only API (new `/superadmin` router)

Guarded by a `require_superadmin` dependency (rejects any non-superadmin with
403). Routes operate cross-org and do **not** use acting-org scoping.

- `GET /superadmin/orgs` — list all orgs with light aggregate counts (users,
  brands) and status.
- `POST /superadmin/orgs` — **onboard**: create org + `plan_code`, create the
  first admin `User` (`role="admin"`, `email_verified=False`), and issue an
  invite/verification email. Reuses `_issue_verification_token`
  (`backend/app/routers/auth.py:47`) and `send_verification_email`.
- `PATCH /superadmin/orgs/{id}` — edit `name` and/or `plan_code`.
- `POST /superadmin/orgs/{id}/suspend` and `POST /superadmin/orgs/{id}/unsuspend`.
- `DELETE /superadmin/orgs/{id}` — delete the org and its data (cascade).
- `GET /superadmin/orgs/{id}/users` — list users in the org.
- `POST /superadmin/orgs/{id}/users` — create a user (role selectable).
- `PATCH /superadmin/orgs/{id}/users/{user_id}` — change role / disable / re-enable.
- `DELETE /superadmin/orgs/{id}/users/{user_id}` — remove a user.
- `POST /superadmin/orgs/{id}/users/{user_id}/reset-password` — trigger a
  password reset / set a temporary password.

(Exact request/response schemas are deferred to the implementation plan.)

### 4.4 Suspend support (schema)

- Add `organizations.status` (`active` | `suspended`, default `active`) via an
  Alembic migration.
- Login (`/auth/login`) and token refresh (`/auth/refresh`) reject users whose
  org is `suspended` (clear, machine-readable error code).
- A superadmin acting-as **can** still enter a suspended org to inspect/fix it
  (the acting-org path does not apply the suspend gate).

### 4.5 Frontend

- **Login routing:** in `AuthContext`, if `user.role === "superadmin"`, redirect
  to `/superadmin` instead of `/brands`.
- **Acting-org plumbing:** store the acting-org id in a cookie
  (`100xai_acting_org`) so both client `apiRequest` and server components can
  attach `X-Acting-Org-Id`. Single edit in `frontend/lib/api.ts` (client branch
  reads `document.cookie`; server branch reads it via `next/headers`). The proxy
  already forwards the header.
- **`/superadmin` landing page:** a table of all orgs (name, plan, status, user
  count, brand count) with row actions — Enter, Edit, Manage users,
  Suspend/Unsuspend, Delete — plus a "Create organization" button that opens the
  onboarding form.
- **"Acting as &lt;Org&gt;" banner:** a persistent top bar shown whenever an
  acting-org cookie is set, with an **Exit** button (clears the cookie and
  returns to `/superadmin`). While acting, the rest of the app is the
  **existing** `/brands` dashboard, untouched.
- **Manage-users view:** per-org user list with create / change-role / disable /
  reset-password actions.

### 4.6 Audit & safety

- Log every superadmin action to `audit_logs` (the table already supports
  `user_id` + `org_id` + `action` + metadata): onboard, edit org, suspend,
  unsuspend, delete, user create/modify/delete/reset, **and** entering an org.
- Destructive actions (delete org) require a typed confirmation in the UI.

## 5. Components & boundaries

| Unit | Responsibility | Depends on |
|------|----------------|------------|
| `rbac.require_role` change | superadmin satisfies any role gate | — |
| `get_acting_context` dep | resolve effective org for superadmin via header | JWT decode, org lookup |
| `require_superadmin` dep | guard `/superadmin/*` routes | JWT decode |
| `/superadmin` router + service | cross-org CRUD, onboarding, suspend | org/user models, email, audit |
| seed script / CLI | provision superadmins from env | org/user models |
| `organizations.status` migration | suspend support | Alembic |
| login/refresh suspend gate | block suspended orgs | `organizations.status` |
| `lib/api.ts` acting-org header | attach `X-Acting-Org-Id` from cookie | cookie |
| `/superadmin` UI + banner | landing, management, acting-as UX | api client |

## 6. Testing

- **Backend**
  - `require_role` lets `superadmin` pass every allowed-set; non-superadmin still
    gated.
  - `X-Acting-Org-Id` is honored for superadmin (reads + writes scoped to target
    org) and **ignored** for non-superadmins (security regression test).
  - Acting on a non-existent org → 404.
  - `require_superadmin` rejects non-superadmins (403) on `/superadmin/*`.
  - Onboarding creates org + admin user + verification token, sends email.
  - Suspend blocks login/refresh; unsuspend restores; acting-as bypasses suspend.
  - Seed script is idempotent.
- **Frontend**
  - Superadmin login redirects to `/superadmin`; normal user to `/brands`.
  - Entering an org sets the cookie and shows the banner; Exit clears it.
  - `X-Acting-Org-Id` is attached on client and server requests while acting.

## 7. Out of scope

- Aggregate platform-metrics tiles (counts dashboards) — not requested.
- Multi-org membership for normal users.
- Impersonating a *specific* user within an org (superadmin acts as org admin,
  not as a named end-user).
- Soft-delete / recoverability of deleted orgs (delete is a hard cascade,
  matching current brand-delete behavior).
