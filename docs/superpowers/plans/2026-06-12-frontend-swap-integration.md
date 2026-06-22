# Swap to 100x-tool-frontend + Backend Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the new `100x-tool-frontend` the project's frontend (so `pnpm dev:web` / `npm run dev` serves the cream/green/orange app, not the old white/blue one), wire it to the existing backend for the blog workflow (brand DNA + keyword/SERP/content pipelines + blog generation + scheduling + publishing), and hide the social-planner/persona pages.

**Architecture:** Replace the contents of `pr/frontend` (the pnpm workspace member named `frontend`) with the new app, keeping the workspace name so `pnpm --filter frontend dev` keeps working. Resolve the 13 outstanding git merge-conflict blocks so it compiles. Fix the API proxy so it forwards the **logged-in user's** JWT instead of a static demo token, then turn off demo mode so pages render live backend data. Remove the planner/persona/social routes and their nav entries.

**Tech Stack:** pnpm monorepo (`pnpm@9.15.0`, workspace = `frontend` + `packages/*`); Next.js 14 App Router + TypeScript; FastAPI backend at `http://localhost:8000` (cookie/JWT auth via `/v1/auth/*`).

---

## Context an implementer needs

**Current state (verified):**
- `pr/` is a pnpm monorepo. Root `package.json` script `dev:web` = `pnpm --filter frontend dev`; workspace members (`pnpm-workspace.yaml`) are `frontend` and `packages/*`.
- The live frontend is `pr/frontend` (white bg `#f9fafb`, indigo accent `#4f46e5`). The new app is `/Users/shubhamrathod/Downloads/100x-tool-frontend` (cream bg `#FAFAF6`, green `#1F3D2E` + orange `#D9572F`). **Both** are named `frontend` in package.json and both use npm `package-lock.json`. The new folder has **no** `.git` of its own.
- The new app **does not compile** — 13 git merge-conflict blocks ("Updated upstream" vs "Stashed changes") across: `lib/api.ts` (4), `lib/types.ts` (3), `app/layout.tsx` (2), `app/brands/[id]/page.tsx` (1), `app/brands/[id]/integrations/wordpress/page.tsx` (3, including a ~360-line block that is essentially two whole versions of the file). `lib/api.ts` also has a duplicate `startSerpAnalysis`.
- **Auth inconsistency:** `middleware.ts` + `context/AuthContext.tsx` implement real cookie-JWT auth (login → `/v1/auth/login`, sets `100xai_access_token` cookie, `getValidAccessToken()` refreshes). But the API proxy `app/api/[...path]/route.ts` **strips the incoming `Authorization` header and injects a static `API_TOKEN`** from `.env.local` (a hardcoded JWT that expires). That static token is a demo crutch and must not be the production auth path.
- The new app's `/brands/*` pages mirror the backend's real routes (verified earlier — auth, brands, profile/DNA, keywords, SERP, pipeline-status, blogs, sources, integrations, schedules, billing all map to existing endpoints). The new app additionally has `/planner/*`, `/persona`, `/onboarding` (social planner + persona) which have **no backend** and are out of scope.

**Decisions (from the requester):**
- Keep the new cream/green/orange theme as-is (no re-theming).
- Physically swap the new app into `pr/frontend`.
- Hide the planner/persona/social pages from the app.
- Integration scope: brand DNA + keyword/SERP/content pipelines + blog generation + scheduling + publishing. No social, no persona backend.

**Decisions (made here, with rationale):**
- **Preserve git history of the swap** via `git rm -r` + copy + `git add` in the `pr` repo, in one commit, so the change is reviewable and revertable. Back up the old frontend to a branch first.
- **Auth = real per-user JWT.** Change the proxy to forward the caller's token (from the `100xai_access_token` cookie or incoming `Authorization`) instead of injecting `API_TOKEN`. Remove `API_TOKEN` from `.env.local`. This gives correct multi-user auth and still avoids CORS (same-origin `/api/*`).
- **Don't fight the package manager.** The new app ships a `package-lock.json`, but the monorepo is pnpm. After the swap, delete `package-lock.json` and let pnpm resolve from the workspace (`pnpm install` at repo root), so `pnpm --filter frontend dev` works. Keep the new app's `package.json` deps.

**Verification baseline:** the backend must be runnable at `http://localhost:8000` (see `pr/backend`, `venv/bin/uvicorn app.main:app` or docker compose) with a seeded user to log in as. Confirm before Task 6.

---

### Task 1: Back up the old frontend, swap the new app into `pr/frontend`

**Goal:** After this task, `pr/frontend` contains the new app's source and `pnpm --filter frontend dev` launches the cream app (it will not fully compile yet — conflicts resolved in Task 2).

- [ ] **Step 1: Safety branch + clean tree check**

```bash
cd /Users/shubhamrathod/Downloads/pr
git status --short            # note any unrelated dirty files; do not discard them
git branch backup/old-frontend-2026-06-12   # snapshot current state (old frontend reachable here)
```

- [ ] **Step 2: Remove the old frontend source (keep node_modules out of git)**

```bash
cd /Users/shubhamrathod/Downloads/pr
git rm -r --quiet frontend
# git rm leaves the dir if node_modules (untracked) remains; clear tracked files only.
```

If `frontend/node_modules` or other untracked artifacts remain, leave them — they'll be overwritten in Step 3.

- [ ] **Step 3: Copy the new app in (excluding build/deps/git-irrelevant dirs)**

```bash
cd /Users/shubhamrathod/Downloads/pr
rm -rf frontend
rsync -a --exclude node_modules --exclude .next --exclude .git \
  /Users/shubhamrathod/Downloads/100x-tool-frontend/ frontend/
```

- [ ] **Step 4: Reconcile package manager to pnpm**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
rm -f package-lock.json          # monorepo is pnpm; let workspace resolve
cd /Users/shubhamrathod/Downloads/pr
pnpm install                     # resolves frontend deps into the workspace
```

Expected: install succeeds. If pnpm complains about the lockfile being out of date, run `pnpm install --no-frozen-lockfile`.

- [ ] **Step 5: Stage the swap (do not commit yet — it won't compile until Task 2)**

```bash
cd /Users/shubhamrathod/Downloads/pr
git add frontend
git status --short | head        # confirm only frontend/ (and pnpm-lock.yaml) changed
```

- [ ] **Step 6: Confirm the dev command now targets the new app**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
grep -n '"name"\|"dev"' package.json   # name must still be "frontend"; dev = "next dev"
```

Do NOT commit here; Task 2 finishes the compilable state, then one combined commit. (If you prefer a checkpoint commit, commit with `--no-verify` and a `wip:` message — but the conflicts make the build red, so a single post-Task-2 commit is cleaner.)

---

### Task 2: Resolve the 13 merge conflicts so the app compiles

**Files (conflict blocks):** `frontend/lib/api.ts` (4 + duplicate `startSerpAnalysis`), `frontend/lib/types.ts` (3), `frontend/app/layout.tsx` (2), `frontend/app/brands/[id]/page.tsx` (1), `frontend/app/brands/[id]/integrations/wordpress/page.tsx` (3).

**Approach:** These are `git stash`-style conflicts ("Updated upstream" = the branch state; "Stashed changes" = newer local work). Resolve each by **reading both sides and taking the union that preserves the newest API surface**, not by blindly picking one side. After each file, the markers (`<<<<<<<`, `=======`, `>>>>>>>`) must be gone.

- [ ] **Step 1: Resolve `frontend/lib/types.ts`**

Read all 3 blocks. These are type definitions — keep the superset of fields/types from both sides (a type present on only one side should survive). Remove markers. This file has no logic, so union is safe.

- [ ] **Step 2: Resolve `frontend/lib/api.ts`**

Read all 4 blocks. Keep the union of API functions. **Remove the duplicate `startSerpAnalysis`** (keep the one matching the backend contract: `POST /v1/brands/{id}/serp-analysis`). Ensure every function still referenced by pages exists exactly once. Note: this file is also edited in Task 3 (auth) and Task 5 (path fixes) — only resolve conflicts here.

- [ ] **Step 3: Resolve `frontend/app/layout.tsx`**

Block 1 (imports) + block 2 (body/providers). Keep the version that wires `AuthProvider` + the scheduler/Terms providers and the global CSS import. Prefer the side that renders the real auth-gated shell.

- [ ] **Step 4: Resolve `frontend/app/brands/[id]/page.tsx`** (1 block) — union the brand-detail data/markup; keep the side that calls the real `getBrand`.

- [ ] **Step 5: Resolve `frontend/app/brands/[id]/integrations/wordpress/page.tsx`** (3 blocks, one ~360 lines = two whole file versions). Read both whole versions. Pick the one that matches the current backend WordPress integration contract (`POST /v1/brands/{id}/integrations/wordpress`, `/wordpress/test`), then re-apply any unique improvements from the other side. When in doubt, prefer the version whose API calls match `frontend/lib/api.ts` after Step 2.

- [ ] **Step 6: Verify no markers remain and it typechecks**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
grep -rn '^<<<<<<<\|^=======\|^>>>>>>>' app lib components ; echo "exit:$?"   # want: no matches
npx tsc --noEmit
```

Expected: no conflict markers; `tsc` clean (or only errors that Task 3/4/5 will address — if so, note them precisely).

- [ ] **Step 7: Commit the swap + conflict resolution together**

```bash
cd /Users/shubhamrathod/Downloads/pr
git add frontend pnpm-lock.yaml
git commit -m "feat: replace frontend with 100x-tool-frontend (cream theme), resolve merge conflicts

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Auth — proxy forwards the real user token

**File:** `frontend/app/api/[...path]/route.ts`, `frontend/.env.local`, `frontend/lib/config.ts`

The proxy currently strips `Authorization` and injects the static `API_TOKEN`. Change it to forward the logged-in user's JWT.

- [ ] **Step 1: Forward the caller's token in the proxy**

In `frontend/app/api/[...path]/route.ts`, replace the header logic so it:
1. Does NOT strip `authorization` from the incoming request (keep it if present), AND
2. If no `Authorization` header is present, reads the `100xai_access_token` cookie and sets `Authorization: Bearer <cookie>`.
3. Remove the `getServerApiToken()` / static `API_TOKEN` injection.

Concrete: keep the `authorization` header in the copy loop (remove the `&& name.toLowerCase() !== "authorization"` exclusion), then after the loop:

```typescript
if (!headers.has("authorization")) {
  const cookieToken = request.cookies.get("100xai_access_token")?.value;
  if (cookieToken) headers.set("authorization", `Bearer ${cookieToken}`);
}
```

Delete the `const token = getServerApiToken(); if (token) headers.set("authorization", ...)` block and the now-unused import.

- [ ] **Step 2: Clean env + config**

In `frontend/.env.local`: set `NEXT_PUBLIC_DEMO_MODE=false`, keep `BACKEND_URL=http://localhost:8000`, and **remove the `API_TOKEN=...` line**. In `frontend/lib/config.ts`, leave `getServerApiToken` if other code still imports it, otherwise remove it; ensure nothing breaks typecheck.

- [ ] **Step 3: Verify client calls carry the token**

Confirm `frontend/lib/api.ts` client requests attach the user token (via `getValidAccessToken()` / cookie) the way `AuthContext` expects — if client calls go through the same-origin `/api/*` proxy, the cookie is sent automatically and Step 1 handles it; if any call hits the backend directly, it must attach `Authorization` from `getValidAccessToken()`. Make them consistent (prefer routing all client calls through `/api/*`).

- [ ] **Step 4: Typecheck + commit**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend && npx tsc --noEmit
cd /Users/shubhamrathod/Downloads/pr
git add frontend/app/api frontend/.env.local frontend/lib/config.ts frontend/lib/api.ts
git commit -m "feat: proxy forwards real user JWT, drop static API_TOKEN, demo mode off

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Hide planner / persona / social pages

**Goal:** The shipped app exposes only the blog workflow. Remove the routes and any nav entries pointing at them.

- [ ] **Step 1: Find every reference**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
grep -rn "/planner\|/persona\|/onboarding\|scheduler" app components lib | grep -v "node_modules"
```

(`/brands/[id]/schedule` is the REAL blog scheduler — keep it. The thing to remove is the social `/planner/*`, `/persona`, `/onboarding`, and `components/scheduler/*` + `lib/scheduler/*` if unused elsewhere.)

- [ ] **Step 2: Remove the route directories and dead components**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
git rm -r "app/planner" "app/persona" "app/onboarding" components/scheduler
# Remove lib/scheduler and lib/demo-data only if grep shows nothing else imports them:
grep -rn "lib/scheduler\|demo-data\|scheduler/persona" app components lib | grep -v node_modules
# if clean, also: git rm -r lib/scheduler ; git rm lib/demo-data.ts
```

- [ ] **Step 3: Remove nav links to those routes**

Edit the nav/sidebar/topbar components (found in Step 1 — likely the brands layout `app/brands/layout.tsx` or a shared nav) to delete any links to `/planner`, `/persona`, `/onboarding`. Remove now-unused imports.

- [ ] **Step 4: Verify no dangling references + typecheck**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
grep -rn "/planner\|/persona\|/onboarding\|components/scheduler\|lib/scheduler" app components lib | grep -v node_modules   # want: empty
npx tsc --noEmit
```

Expected: no references, clean typecheck. Fix any import that broke.

- [ ] **Step 5: Commit**

```bash
cd /Users/shubhamrathod/Downloads/pr
git add frontend
git commit -m "chore: remove social planner/persona/onboarding pages and nav

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Reconcile API paths + verify the blog workflow contract

**Goal:** Every page in the blog workflow calls an endpoint that actually exists on the backend. Fix mismatches.

- [ ] **Step 1: Extract the frontend's called paths**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
grep -rEon "\`?/v1/[a-zA-Z0-9_/{}$.-]+" lib/api.ts | sort -u
```

- [ ] **Step 2: Diff against the backend route list**

The backend (verified) exposes under `/v1`: `auth/*`; `brands`, `brands/{id}`, `brands/{id}/onboarding-status`, `brands/{id}/profile`, `brands/{id}/approve`, `brands/{id}/keywords[/research|/stats]`, `brands/{id}/serp-analysis`, `brands/{id}/pipeline-status`; `brands/{id}/sources[/reingest]`; `brands/{id}/blogs[/{jobId}[/approve-brief|reject-brief|approve-article|reject-article|retry]]`; `brands/{id}/content-generation`; `jobs/{id}`; `brands/{id}/integrations[...]`; `schedules/brands/{id}/bulk|calendar|review-queue`, `schedules/{id}[/approve|reject]`; `publishing/*`; `billing/*`. For each frontend path with no backend match, either fix the frontend path or note the gap. (Persona/social paths should already be gone after Task 4.)

- [ ] **Step 3: Fix mismatches in `frontend/lib/api.ts`** to match the backend exactly. Common suspects: trailing slashes, `serp-analysis` start payload (`{}`), blog scheduling `bulk` body shape (`{items:[{date,keyword}], time, timezone_str, channels?}`).

- [ ] **Step 4: Typecheck + commit**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend && npx tsc --noEmit
cd /Users/shubhamrathod/Downloads/pr
git add frontend/lib/api.ts
git commit -m "fix: align frontend API paths with backend routes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Build, run, and smoke-test against the live backend

- [ ] **Step 1: Production build**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend && npx next build
```

Expected: build succeeds (fix any remaining type/route errors it surfaces).

- [ ] **Step 2: Start backend + frontend**

Start the backend (`cd /Users/shubhamrathod/Downloads/pr/backend && venv/bin/uvicorn app.main:app --port 8000`, plus the worker/redis/postgres it needs), then:

```bash
cd /Users/shubhamrathod/Downloads/pr && pnpm dev:web   # serves the NEW cream app on :3000
```

- [ ] **Step 3: Smoke test the blog workflow (manual, in browser)**
  - Visit `/` → redirected to `/login` (middleware). Log in with a seeded user → lands on `/brands`, cream theme.
  - `/brands` lists real brands from the backend (not demo). Open a brand → DNA, keywords, SERP, jobs, sources, integrations all load live data.
  - Start a blog (keyword) → job runs → brief/article review → approve → publishes. Scheduling page (`/brands/[id]/schedule`) shows the real calendar.
  - Confirm in the network tab that `/api/v1/*` calls carry the logged-in user's token (Task 3) and return 200s, not 401s.
  - Confirm there is no `/planner`, `/persona`, or `/onboarding` route and no nav link to them.

- [ ] **Step 4: Note any runtime gaps** (pages that 404/401/500 against the backend) and fix or record them. Done when the blog workflow works end-to-end on the new frontend.

---

## Out of scope / follow-ups
- **Publishing to Shopify/Webflow/custom-webhook from blog approval.** `blogs.py` `approve-article` currently publishes only to WordPress; broadening it is a separate backend task (the integrations + publishing layers already support the other channels).
- **Persona backend** — covered by the separate `2026-06-12-persona-api.md` plan; deferred (planner/persona pages are removed here).
- **Re-theming** — none; the cream/green/orange theme is kept as-is per the requester.
- **CI / deploy config** that referenced the old frontend path (unchanged path `pr/frontend`, so likely fine — verify if CI exists).
