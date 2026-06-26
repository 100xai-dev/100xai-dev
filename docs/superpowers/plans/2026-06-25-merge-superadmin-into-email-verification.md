# Merge `feat/superadmin` into Email-Verification Branch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the platform-superadmin feature into `feat/email-verification-razorpay-terms` and deploy it to the server without breaking the running app (especially login).

**Architecture:** A standard merge commit (Approach A) brings 17 superadmin commits onto the email-verification branch. The only conflict is one line in `backend/requirements.txt`. Because the email-verification branch made *zero* backend/frontend code changes since the merge-base, the merged tree's code is identical to the already-tested `feat/superadmin` branch — verified by `git diff`. Deployment runs the additive DB migration *before* swapping in the new code so live queries never hit missing columns.

**Tech Stack:** git, Docker Compose, Alembic, FastAPI, Postgres 16.

**Spec:** `docs/superpowers/specs/2026-06-25-merge-superadmin-into-email-verification-design.md`

---

## Critical safety notes (read before starting)

- **Do NOT run the backend test suite inside the api/worker containers.** Tests are excluded from the images by `.dockerignore`, and `backend/tests/conftest.py` falls back to `DATABASE_URL` when `TEST_DATABASE_URL` is unset — inside a container `DATABASE_URL` points at **production Postgres**, and the fixture calls `Base.metadata.drop_all()`. Running it there would wipe the production database. The correctness gate in this plan is a `git diff` against the already-tested branch (Task 2), not an in-container test run.
- The migration `20260619_0014_superadmin.py` is **additive only** (`organizations.status` default `"active"`, `users.disabled` default `false`). It is backward-compatible: old code ignores the new columns, so it is safe to run before the new code is live.

---

## Phase 1 — Local: produce the merged branch

### Task 1: Create the merge commit and resolve the one conflict

**Files:**
- Modify: `backend/requirements.txt` (conflict resolution)

- [ ] **Step 1: Confirm a clean working tree on the target branch**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
git checkout feat/email-verification-razorpay-terms
git status --short
```
Expected: no output (clean tree). If anything is listed, stop and stash/commit it first.

- [ ] **Step 2: Make sure both branches are up to date with the remote**

Run:
```bash
git fetch origin
git log -1 --oneline origin/feat/superadmin
git log -1 --oneline origin/feat/email-verification-razorpay-terms
```
Expected: the local branches match origin. If `feat/superadmin` is behind origin, run `git branch -f feat/superadmin origin/feat/superadmin`.

- [ ] **Step 3: Start the merge (it WILL conflict on requirements.txt)**

Run:
```bash
git merge --no-ff feat/superadmin
```
Expected: output ends with
```
CONFLICT (content): Merge conflict in backend/requirements.txt
Automatic merge failed; fix conflicts and then commit the result.
```

- [ ] **Step 4: Resolve `backend/requirements.txt` — keep the commented line**

Open `backend/requirements.txt`. Replace the entire conflict block:
```
<<<<<<< HEAD
pinecone>=5.0.0  # renamed from `pinecone-client`; v3+ API (Pinecone/ServerlessSpec) used in ingestion.py
=======
pinecone>=5.0.0
>>>>>>> feat/superadmin
```
with this single line (keep HEAD's commented version — functionally identical, more informative):
```
pinecone>=5.0.0  # renamed from `pinecone-client`; v3+ API (Pinecone/ServerlessSpec) used in ingestion.py
```

- [ ] **Step 5: Confirm no conflict markers remain**

Run:
```bash
grep -rn '^<<<<<<<\|^=======\|^>>>>>>>' backend/requirements.txt
```
Expected: no output.

- [ ] **Step 6: Stage and complete the merge commit**

Run:
```bash
git add backend/requirements.txt
git commit --no-edit
git log -1 --oneline
```
Expected: a merge commit like `Merge branch 'feat/superadmin' into feat/email-verification-razorpay-terms`.

---

### Task 2: Verify the merged code equals the tested branch (correctness gate)

**Files:** none (verification only)

- [ ] **Step 1: Diff backend code against the tested superadmin branch**

Run:
```bash
git diff feat/superadmin HEAD -- backend/app backend/alembic backend/tests
```
Expected: **no output.** This proves all superadmin backend code, migration, and tests landed unchanged.

- [ ] **Step 2: Diff requirements.txt — only the comment should differ**

Run:
```bash
git diff feat/superadmin HEAD -- backend/requirements.txt
```
Expected: the only difference is the trailing `# renamed from ...` comment on the `pinecone` line. No version or package-name change.

- [ ] **Step 3: Diff the frontend against the tested branch**

Run:
```bash
git diff feat/superadmin HEAD -- frontend
```
Expected: **no output** (email-verification made no frontend changes).

- [ ] **Step 4: Confirm the docker-compose fix from the email branch survived the merge**

Run:
```bash
grep -n "127.0.0.1:5432\|127.0.0.1:6379\|\$\$REDIS_URL" docker-compose.yml
```
Expected: three matching lines (the loopback bindings and the escaped worker healthcheck). If any are missing, the merge dropped the email-branch infra fix — stop and investigate.

---

### Task 3 (OPTIONAL): Run the backend tests locally in a throwaway venv

Skip this if Task 2 passed cleanly — the merged backend is byte-identical to the already-green `feat/superadmin` branch. Run it only if you want independent confirmation. This uses in-memory SQLite and **never touches any real database**.

**Files:** none (creates a disposable `/tmp` venv)

- [ ] **Step 1: Create an isolated venv and install backend deps**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr/backend
python3 -m venv /tmp/sa-merge-venv
/tmp/sa-merge-venv/bin/pip install -q -r requirements.txt
```
Expected: installs without error (may take a few minutes).

- [ ] **Step 2: Run the superadmin-related tests with NO database env set**

Run (the leading `env -u` guarantees SQLite fallback in conftest):
```bash
cd /Users/shubhamrathod/Downloads/pr/backend
env -u DATABASE_URL -u TEST_DATABASE_URL PYTHONPATH=. \
  /tmp/sa-merge-venv/bin/pytest tests/test_superadmin.py tests/test_acting_context.py tests/test_superadmin_seed.py tests/test_auth.py -q
```
Expected: all tests pass (`N passed`).

- [ ] **Step 3: Clean up the venv**

Run:
```bash
rm -rf /tmp/sa-merge-venv
```

---

### Task 4: Push the merged branch

**Files:** none

- [ ] **Step 1: Push**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
git push origin feat/email-verification-razorpay-terms
```
Expected: push succeeds, fast-forwarding `origin/feat/email-verification-razorpay-terms` to the new merge commit.

- [ ] **Step 2: Confirm remote is updated**

Run:
```bash
git log -1 --oneline origin/feat/email-verification-razorpay-terms
```
Expected: shows the merge commit hash.

---

## Phase 2 — Server: deploy without breakage

All commands run on the server: `ssh` in, then `cd /home/100xai/100xai-app`.

### Task 5: Pull the merged branch on the server

- [ ] **Step 1: Check for local edits that would block the pull**

Run:
```bash
cd /home/100xai/100xai-app
git status --short
```
Expected: clean. If `docker-compose.yml` shows as modified (edited directly on the server earlier), run `git stash` first, then pull, then reconcile.

- [ ] **Step 2: Pull**

Run:
```bash
git pull
```
Expected: fast-forward merge pulling the superadmin files + the merge commit.

---

### Task 6: Configure superadmin provisioning

**Files:**
- Modify: `backend/.env` (server-only, not in git)

- [ ] **Step 1: Add the superadmin settings**

Append to `backend/.env` (replace with the operator-provided address(es)):
```bash
SUPERADMIN_EMAILS=<your-superadmin-email>          # comma-separated for multiple
SUPERADMIN_PASSWORD=<choose-a-strong-password>     # optional; omit to get a generated one in logs
```

- [ ] **Step 2: Confirm the values are present**

Run:
```bash
grep -E "SUPERADMIN_EMAILS|SUPERADMIN_PASSWORD" backend/.env
```
Expected: the two lines you just added.

---

### Task 7: Build the new images (old containers keep serving)

- [ ] **Step 1: Build**

Run:
```bash
docker compose build api worker frontend
```
Expected: all three images build successfully. The running containers are untouched until Task 9.

---

### Task 8: Run the additive migration (before swapping in code)

- [ ] **Step 1: Check current revision**

Run:
```bash
docker compose run --rm -w /app/backend api alembic current
```
Expected: shows `20260612_0013` (the revision before superadmin).

- [ ] **Step 2: Upgrade to head**

Run:
```bash
docker compose run --rm -w /app/backend api alembic upgrade head
```
Expected: log line `Running upgrade 20260612_0013 -> 20260619_0014, superadmin: organization status + user disabled`.

- [ ] **Step 3: Confirm the new revision**

Run:
```bash
docker compose run --rm -w /app/backend api alembic current
```
Expected: `20260619_0014 (head)`.

- [ ] **Step 4: Spot-check the new columns exist with safe defaults**

Run:
```bash
docker compose exec postgres psql -U 100xai -d 100xai -c "\d organizations" -c "\d users" | grep -E "status|disabled"
```
Expected: `status | character varying | not null default 'active'` and `disabled | boolean | not null default false`.

---

### Task 9: Swap in the new code

- [ ] **Step 1: Bring up the new containers**

Run:
```bash
docker compose up -d
```
Expected: api, worker, frontend recreated; postgres/redis/minio/caddy unchanged.

- [ ] **Step 2: Wait for health**

Run:
```bash
docker compose ps
```
Expected: api/worker/frontend report `(healthy)` within ~30–60s. Re-run until healthy.

---

### Task 10: Seed the superadmin account(s)

- [ ] **Step 1: Run the seed script**

Run:
```bash
docker compose exec -w /app/backend api python -m app.scripts.seed_superadmins
```
Expected: `Seeded N superadmin(s).` If you omitted `SUPERADMIN_PASSWORD`, the log line `Created superadmin <email> with generated password: <pw>` appears once — copy it now.

- [ ] **Step 2: Confirm the superadmin row**

Run:
```bash
docker compose exec postgres psql -U 100xai -d 100xai -c "SELECT email, role, email_verified, disabled FROM users WHERE role='superadmin';"
```
Expected: your email with `role=superadmin`, `email_verified=t`, `disabled=f`.

---

### Task 11: Verify nothing broke

- [ ] **Step 1: API health**

Run:
```bash
curl --fail --silent https://api.100xai.co/health && echo OK
```
Expected: `OK`.

- [ ] **Step 2: An existing (non-superadmin) user can still log in**

Log in through the app UI (or hit the login endpoint) with a pre-existing account. Expected: login succeeds — confirms the new org/user gating did not lock anyone out (existing rows defaulted to `active` / not-`disabled`).

- [ ] **Step 3: Superadmin can log in and reach `/superadmin`**

Log in with the seeded superadmin account. Expected: redirected to `/superadmin`, the orgs landing page loads.

- [ ] **Step 4: No error spam in logs**

Run:
```bash
docker compose logs --since=5m api worker | grep -iE "error|traceback|undefinedcolumn|does not exist" | head
```
Expected: no `UndefinedColumn` / `column ... does not exist` errors.

---

## Rollback (if Task 9 or 11 reveals a real break)

The migration is additive, so the columns can safely remain. To revert the *code*:

- [ ] **Step 1: Check out the previous deployed commit**

Run on the server:
```bash
git log --oneline -5          # find the commit before the merge (the infra-fix commit cd31f3b)
git checkout cd31f3b -- docker-compose.yml   # or: git reset --hard <previous-commit> if a full code revert is needed
docker compose up -d --build
```

- [ ] **Step 2 (only if columns must go too):** `docker compose run --rm -w /app/backend api alembic downgrade -1` — drops `users.disabled` and `organizations.status`. Only do this after the old code is back, since the old code doesn't use those columns anyway.

---

## Success criteria

- `git diff feat/superadmin HEAD -- backend/app backend/alembic backend/tests frontend` is empty (Task 2).
- `docker-compose.yml` loopback + `$$REDIS_URL` fixes survived the merge (Task 2 Step 4).
- `alembic current` reports `20260619_0014 (head)` on the server (Task 8).
- An existing user and the seeded superadmin can both log in (Task 11).
- No `column does not exist` errors in api/worker logs (Task 11 Step 4).
