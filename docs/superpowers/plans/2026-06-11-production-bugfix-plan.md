# 100xAI Pre-Production Bugfix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the verified security and correctness bugs found in the pre-production audit of the 100xAI platform (FastAPI backend, RQ worker, Next.js frontend, infra) so the system is safe to deploy.

**Architecture:** Monorepo with `backend/` (FastAPI + SQLAlchemy 2.0 + Alembic + RQ), `frontend/` (Next.js App Router), `infra/docker/`, and CI in `.github/workflows/ci.yml`. Fixes are grouped by severity: secret/credential leaks first (P0), then auth/SSRF/XSS (P1), then runtime-crash and correctness bugs (P2), then hardening (P3).

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0.x, Alembic, Redis/RQ, PyJWT, bcrypt, Razorpay SDK, Next.js 14 (App Router), TypeScript, Docker Compose.

---

## How to use this plan

- Each task is self-contained with exact file paths and line numbers (verified against the repo on 2026-06-11).
- The repo's `.claude/CLAUDE.md` instructs you to use the `vexp` MCP pipeline. **Its index points at the wrong directory and returns junk** — ignore it and use `Read`/`grep` directly.
- **P0 tasks involve real leaked credentials that must be rotated by a human.** The plan tells you exactly what to rotate; the code changes are yours, the rotation is the operator's.
- Run the backend test suite after each backend task: `cd backend && PYTHONPATH=. python -m pytest -p no:rerunfailures tests -q`

---

## Bug inventory (verified)

| # | Severity | Area | Bug | Task |
|---|----------|------|-----|------|

| 4 | CRITICAL | auth | JWT secret defaults to public string `dev-secret-change-me-...`, no prod guard; live `.env` uses it | T3 |
| 5 | CRITICAL | frontend | LLM-generated blog HTML rendered via `dangerouslySetInnerHTML` (stored XSS) | T9 |                                
| 6 | CRITICAL | backend | SSRF in brand crawler — fetches user URL with no private-IP block, follows redirects | T6 |
| 7 | HIGH | infra | docker-compose exposes Postgres/Redis(no-auth)/MinIO on all interfaces with default creds | T4 |
| 8 | HIGH | runtime | `func.case([...])` (SQLAlchemy-1.x list form) → 4 publishing endpoints 500 | T5 |
| 9 | HIGH | runtime | `logger` used but never imported in `brands.py` → `NameError` masks SERP errors | T5 |
| 10 | HIGH | worker | `publish_approv
ed_schedule` not idempotent → double-publish on RQ retry | T7 |
| 11 | HIGH | infra/CI | CI install step fails (flat-layout pkg discovery) → tests never run; alembic cwd bug; missing deps | T8 |
| 12 | HIGH | frontend | JWT access+refresh tokens in `localStorage`; cookie without `Secure`/`HttpOnly` | T10 |
| 13 | HIGH | frontend | Hardcoded `http://localhost:8000` fallback in client bundles → prod breakage/mixed-content | T11 |
| 14 | HIGH | frontend | Middleware redirects signed-in users away from `/terms` they must read | T12 |
| 15 | MEDIUM | backend | CORS substring match (`.ngrok.io` in origin) + credentials → cross-origin read | T13 |
| 16 | MEDIUM | backend | No rate limiting on login/signup/resend → brute force + enumeration | T14 |
| 17 | MEDIUM | backend | SSRF in `publishing.test-connection` + `integrations.test_webhook_config` (sync call blocks loop) | T15 |
| 18 | MEDIUM | backend | `publishing.health` not org-scoped → cross-tenant queue stats leak | T16 |
| 19 | MEDIUM | frontend | API proxy forwards any path with no auth/allowlist → full backend surface exposed | T17 |
| 20 | MEDIUM | backend | Fabricated keyword metrics (`random.randint`) persisted/shown as real SEO data | T18 |
| 21 | MEDIUM | infra | Ops scripts (`fix_completed_job.py`, `manual_serp_requeue.py`) force-mutate prod DB, ship in image | T2 |
| 22 | MEDIUM | infra | `fix_wordpress_user_role.sql` wrong-username typo (`8367` vs `8147`) | T1 |
| 23 | LOW | backend | XML sitemap parsed with stdlib ElementTree (billion-laughs) | T19 |
| 24 | LOW | backend | Login timing leak (bcrypt skipped when user absent) → user enumeration | T14 |
| 25 | LOW | backend | Razorpay webhook idempotency race → spurious 500s on concurrent delivery | T20 |
| 26 | LOW | frontend | Unguarded `JSON.parse` of localStorage hard-crashes app shell | T10 |
| 27 | LOW | frontend | Keywords list `slice(0,20)` with no pagination → only 20 of N visible | T21 |
| 28 | LOW | infra | Migration 0009 uses Python `default=` not `server_default` on NOT NULL cols | T22 |
| 29 | LOW | infra | `.claude/settings.local.json` (live bearer tokens) not in repo `.gitignore` | T2 |

---

## P0 — Stop the credential bleed (do these first, in order)

### Task 1: Remove and rotate hardcoded credentials

**Files:**
- Delete: `backend/test_dataforseo_auth.py`
- Delete: `test_wordpress_connection.py` (repo root)
- Delete: `backend/test_wordpress_connection.py`
- Delete: `backend/debug_wordpress_connection.py`
- Delete: `fix_wordpress_user_role.sql` (repo root)

- [ ] **Step 1: Confirm exactly which tracked files contain live credentials**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
git ls-files | grep -E 'test_dataforseo_auth|test_wordpress_connection|debug_wordpress_connection|fix_wordpress_user_role'
grep -rn "password\|app_password\|login = " backend/test_dataforseo_auth.py test_wordpress_connection.py backend/test_wordpress_connection.py 2>/dev/null
```
Expected: the files listed are tracked; `backend/test_dataforseo_auth.py:8-9` shows `login='shubhamrathod1619@gmail.com'` / `password='uavXu7tE6mr8zgb'`; `test_wordpress_connection.py:11-14` shows the WP `app_password = "GFrz zTOC 4ClR jvoB 4FFM 7ad0"`.

- [ ] **Step 2: Operator action — ROTATE before deleting (cannot be skipped)**

These secrets are already in git history; deletion alone does not protect them. The operator must:
1. Change the DataForSEO account password for `shubhamrathod1619@gmail.com` in the DataForSEO dashboard.
2. Revoke the WordPress application password `GFrz zTOC 4ClR jvoB 4FFM 7ad0` for user `xuyagonete8147` on `assuring-cod-3ba97e.instawp.site` (Users → Profile → Application Passwords → Revoke).

Document completion in `status.md` before proceeding.

- [ ] **Step 3: Delete the credential-bearing scripts**

```bash
cd /Users/shubhamrathod/Downloads/pr
git rm backend/test_dataforseo_auth.py test_wordpress_connection.py backend/test_wordpress_connection.py backend/debug_wordpress_connection.py fix_wordpress_user_role.sql
```

These are ad-hoc manual scripts, not part of `backend/tests/` (CI does not run them). Deleting them removes the leak surface. If the role-fix is genuinely needed operationally, do it via WP-CLI (`wp user set-role xuyagonete8147 administrator`), not committed SQL — note the SQL also had a typo (`8367` on line 24 vs `8147` everywhere else), so it never worked as written.

- [ ] **Step 4: Purge from git history**

```bash
cd /Users/shubhamrathod/Downloads/pr
# Requires: pip install git-filter-repo
git filter-repo --invert-paths \
  --path backend/test_dataforseo_auth.py \
  --path test_wordpress_connection.py \
  --path backend/test_wordpress_connection.py \
  --path backend/debug_wordpress_connection.py \
  --path fix_wordpress_user_role.sql --force
```
Expected: history rewritten. Coordinate force-push with the team (this rewrites SHAs). If `git filter-repo` is unavailable, the rotation in Step 2 is the real mitigation; history scrub can follow.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "security: remove hardcoded DataForSEO/WordPress credentials and one-off SQL"
```

---

### Task 2: Add `.dockerignore`, exclude ops scripts and local settings from images/git

**Files:**
- Create: `.dockerignore`
- Modify: `.gitignore`
- Move: `backend/fix_completed_job.py` → `backend/ops/fix_completed_job.py`
- Move: `backend/manual_serp_requeue.py` → `backend/ops/manual_serp_requeue.py`

- [ ] **Step 1: Create `.dockerignore` at repo root**

```
# .dockerignore — keep secrets, local state, and dev cruft out of build context
**/.env
**/.env.*
!**/.env.example
**/venv
**/.venv
**/__pycache__
**/*.pyc
**/.pytest_cache
**/.ruff_cache
*.db
*.sqlite3
*.log
.git
.github
.claude
docs
**/node_modules
**/.next
backend/test_*.py
backend/debug_*.py
backend/fix_*.py
backend/simple_*.py
backend/manual_*.py
backend/ops
```

- [ ] **Step 2: Verify the backend Dockerfiles no longer pull `.env`**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
docker build -f infra/docker/Dockerfile.backend -t 100xai-backend-test . 2>&1 | tail -5
docker run --rm 100xai-backend-test sh -c 'ls -la /app/backend/.env 2>&1; ls /app/backend/test_*.py 2>&1 | head'
```
Expected: `/app/backend/.env: No such file or directory` and no `test_*.py` present in the image.

- [ ] **Step 3: Operator action — rotate keys in `backend/.env` if any image was ever pushed**

`backend/.env` holds live `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `PINECONE_API_KEY`, `SERPAPI_API_KEY`, `APIFY_API_KEY`, `FIRECRAWL_API_KEY`, Razorpay key/secret, and `WPCOM_CLIENT_SECRET`. If any backend/worker image was pushed to a registry before this fix, rotate all of them. Record in `status.md`.

- [ ] **Step 4: Move ops scripts out of the shipped tree**

```bash
cd /Users/shubhamrathod/Downloads/pr
mkdir -p backend/ops
git mv backend/fix_completed_job.py backend/ops/fix_completed_job.py
git mv backend/manual_serp_requeue.py backend/ops/manual_serp_requeue.py
```
(These force-flip `job.status` and commit against `DATABASE_URL`; they must not be runnable inside a prod container. `.dockerignore` from Step 1 excludes `backend/ops`.)

- [ ] **Step 5: Add local settings + env to `.gitignore`**

In `.gitignore`, append:
```
# local agent settings with bearer tokens
.claude/settings.local.json
# never commit real env files
.env
backend/.env
```
Then ensure it is not currently tracked:
```bash
git rm --cached .claude/settings.local.json 2>/dev/null || true
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "security: add .dockerignore, gitignore local settings, relocate ops scripts"
```

---

### Task 3: Reject default JWT/refresh secrets outside development

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_config.py`:
```python
import pytest
from pydantic import ValidationError
from app.config import Settings


def test_default_jwt_secret_rejected_in_production():
    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            jwt_secret="dev-secret-change-me-at-least-32-chars",
            database_url="postgresql+psycopg://x/y",
        )


def test_real_secret_accepted_in_production():
    s = Settings(
        app_env="production",
        jwt_secret="a-real-randomly-generated-secret-value-32+",
        refresh_token_secret="another-real-randomly-generated-secret-32+",
        database_url="postgresql+psycopg://x/y",
    )
    assert s.jwt_secret.startswith("a-real")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/unit/test_config.py -q`
Expected: FAIL — production default secret is currently accepted (no validator).

- [ ] **Step 3: Add a model validator to `Settings`**

In `backend/app/config.py`, after the field definitions add:
```python
from pydantic import model_validator

_KNOWN_DEFAULT_SECRETS = {
    "dev-secret-change-me-at-least-32-chars",
    "dev-refresh-secret-change-me-at-least-32-chars",
    "local-dev-secret-change-me-at-least-32-chars",
}

    @model_validator(mode="after")
    def _reject_default_secrets_in_prod(self):
        if self.app_env != "development":
            for name in ("jwt_secret", "refresh_token_secret"):
                val = getattr(self, name, None)
                if val in _KNOWN_DEFAULT_SECRETS or (val is not None and len(val) < 32):
                    raise ValueError(
                        f"{name} must be a unique secret of >=32 chars outside development"
                    )
        return self
```
(Place the `_KNOWN_DEFAULT_SECRETS` set at module level and the method inside the `Settings` class.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/unit/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Operator action — set a real `JWT_SECRET` in the deployment env**

Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` and set `JWT_SECRET` and `REFRESH_TOKEN_SECRET` in the production environment (not in any committed file).

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/tests/unit/test_config.py
git commit -m "security: reject default/short JWT secrets outside development"
```

---

### Task 4: Lock down docker-compose service exposure

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Bind data services to loopback and require real passwords**

In `docker-compose.yml`, for the `postgres`, `redis`, and `minio` services:
- Change each `ports` mapping from `"5432:5432"` form to loopback: `"127.0.0.1:5432:5432"`, `"127.0.0.1:6379:6379"`, `"127.0.0.1:9000:9000"`, `"127.0.0.1:9001:9001"`. (Or remove host port mappings entirely — the app talks to them over the compose network by service name.)
- Change `POSTGRES_PASSWORD: 100xai` to `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}` (no insecure fallback).
- Add Redis auth: set command to `redis-server --requirepass ${REDIS_PASSWORD:?set REDIS_PASSWORD}` and update the app/worker `REDIS_URL` to include the password.
- Change MinIO `MINIO_ROOT_PASSWORD: 100xai-dev-secret` fallback to `${MINIO_ROOT_PASSWORD:?set MINIO_ROOT_PASSWORD}`.

- [ ] **Step 2: Verify compose still parses and starts**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
POSTGRES_PASSWORD=test REDIS_PASSWORD=test MINIO_ROOT_PASSWORD=testsecret docker compose config >/dev/null && echo "compose OK"
```
Expected: `compose OK` (config validates; missing-var form errors loudly when unset, which is the goal).

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "security: bind data services to loopback and require non-default credentials"
```

---

## P1 — Runtime crashes and auth/SSRF/XSS

### Task 5: Fix `func.case` crash and missing `logger` in routers

**Files:**
- Modify: `backend/app/routers/publishing.py:55-57,67-68,349`
- Modify: `backend/app/routers/brands.py` (add import at top; `logger` used at line 574)
- Test: `backend/tests/test_publishing_stats.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_publishing_stats.py`:
```python
from sqlalchemy import func, case, select
from app.models.schedule import BlogSchedule, ScheduleStatus


def test_case_expression_compiles():
    # 2.0 positional-when form must compile to valid SQL
    expr = func.count(case((BlogSchedule.status == ScheduleStatus.PUBLISHED, 1)))
    compiled = str(select(expr).compile(compile_kwargs={"literal_binds": True}))
    assert "CASE" in compiled.upper()
```

- [ ] **Step 2: Run test to verify the current (list-form) usage is wrong**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_publishing_stats.py -q`
Expected: PASS for the new positional form — but the production code still uses the broken list form. Confirm the breakage directly:
```bash
cd backend && PYTHONPATH=. python -c "from sqlalchemy import func; from app.models.schedule import BlogSchedule, ScheduleStatus; from sqlalchemy import select; print(str(select(func.count(func.case([(BlogSchedule.status==ScheduleStatus.PUBLISHED,1)]))).compile()))"
```
Expected: produces invalid `count(case(?))` / raises — proving the bug.

- [ ] **Step 3: Replace all six list-form `func.case([...])` calls**

In `backend/app/routers/publishing.py`, change every occurrence from:
```python
func.count(func.case([(<cond>, 1)])).label("<x>"),
```
to:
```python
func.count(case((<cond>, 1))).label("<x>"),
```
(Lines 55, 56, 57, 67, 68, 349.) Ensure `case` is imported: add `case` to the existing `from sqlalchemy import ...` line at the top of the file (it currently imports `func`).

- [ ] **Step 4: Add the missing logger to `brands.py`**

At the top of `backend/app/routers/brands.py` (with the other imports), add:
```python
import logging

logger = logging.getLogger(__name__)
```
This fixes the `NameError` at line 574 (`logger.exception("Failed to enqueue SERP analysis job")`) that currently masks the real failure.

- [ ] **Step 5: Run tests**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS, no import/collection errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/publishing.py backend/app/routers/brands.py backend/tests/test_publishing_stats.py
git commit -m "fix: SQLAlchemy 2.0 case() syntax and missing logger in routers"
```

---

### Task 6: Block SSRF in the brand crawler

**Files:**
- Create: `backend/app/services/url_guard.py`
- Modify: `backend/app/services/crawler.py:142-159,166-198,205-218,245-270`
- Test: `backend/tests/test_url_guard.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_url_guard.py`:
```python
import pytest
from app.services.url_guard import assert_public_url, UnsafeURLError


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost:8000/internal",
    "http://127.0.0.1/x",
    "http://10.0.0.5/x",
    "http://192.168.1.1/x",
    "http://[::1]/x",
    "ftp://example.com/x",
])
def test_rejects_unsafe(url):
    with pytest.raises(UnsafeURLError):
        assert_public_url(url)


def test_allows_public():
    assert_public_url("https://example.com/page")  # no raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_url_guard.py -q`
Expected: FAIL — module does not exist yet.

- [ ] **Step 3: Implement `url_guard.py`**

```python
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    """Raised when a URL targets a non-public or disallowed address."""


_ALLOWED_SCHEMES = {"http", "https"}


def assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"scheme not allowed: {parsed.scheme!r}")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("missing host")
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed for {host!r}") from exc
    for *_, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            raise UnsafeURLError(f"resolves to non-public address: {ip}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_url_guard.py -q`
Expected: PASS.

- [ ] **Step 5: Enforce the guard in the crawler and disable open redirects**

In `backend/app/services/crawler.py`:
- At the top, add `from app.services.url_guard import assert_public_url, UnsafeURLError`.
- In `_fetch_with_httpx` (around line 166) and `_fetch_with_playwright` (around line 205), call `assert_public_url(url)` as the first line; on `UnsafeURLError` return `None` (skip the fetch) and log a warning.
- In the `discover_urls` / sitemap path (around line 142-159), call `assert_public_url(seed_url)` before fetching.
- Change `follow_redirects=True` to `follow_redirects=False` in the `httpx.AsyncClient(...)` calls; if a redirect must be followed, re-run `assert_public_url` on the `Location` header before fetching the next hop. (A redirect to `169.254.169.254` is the classic bypass; not following redirects is the simplest safe default.)

- [ ] **Step 6: Run the full suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/url_guard.py backend/app/services/crawler.py backend/tests/test_url_guard.py
git commit -m "security: block SSRF in brand crawler via public-URL guard"
```

---

### Task 7: Make `publish_approved_schedule` idempotent

**Files:**
- Modify: `backend/worker/tasks/scheduler.py:83-138`
- Test: `backend/tests/test_publish_idempotency.py` (create)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_publish_idempotency.py`. The test simulates a retry where one channel already has a published URL and asserts the provider is not called again for that channel:
```python
from unittest.mock import MagicMock, patch
from app.models.schedule import BlogSchedule, ScheduleStatus


def test_already_published_channel_is_skipped_on_retry(db_session):
    # schedule left in PUBLISHING with wordpress already in published_urls
    sched = BlogSchedule(
        status=ScheduleStatus.PUBLISHING,
        target_channels=["wordpress"],
        published_urls={"wordpress": "https://site/posts/1"},
    )
    db_session.add(sched)
    db_session.commit()

    with patch("app.worker.tasks.scheduler._publish_channel") as pub:
        from app.worker.tasks.scheduler import publish_approved_schedule
        publish_approved_schedule(str(sched.id))
        pub.assert_not_called()  # wordpress already done → no re-publish
```
(Adjust import path to the actual module — `worker.tasks.scheduler` per repo layout — and reuse the `db_session` fixture from `backend/tests/conftest.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_publish_idempotency.py -q`
Expected: FAIL — current loop re-publishes every channel regardless of `published_urls`.

- [ ] **Step 3: Add a per-channel skip guard and commit status before the network call**

In `backend/worker/tasks/scheduler.py`, inside `publish_approved_schedule`:
- After loading the schedule and before the channel loop, persist an in-flight marker and commit so a crash mid-loop is recoverable:
```python
published = dict(schedule.published_urls or {})
channels = schedule.target_channels or ["wordpress"]
for channel in channels:
    if channel in published and published[channel]:
        continue  # already published on a prior attempt — do not duplicate
    published[channel] = _publish_channel(db, schedule, job, draft, channel)
    schedule.published_urls = dict(published)
    db.add(schedule)
    db.commit()  # persist each channel as soon as it succeeds
```
- After the loop, set `schedule.status = ScheduleStatus.PUBLISHED` and `db.commit()`.

This makes a retry resume only the channels not yet recorded in `published_urls`, eliminating duplicate WordPress posts.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_publish_idempotency.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/worker/tasks/scheduler.py backend/tests/test_publish_idempotency.py
git commit -m "fix: make schedule publishing idempotent to prevent duplicate posts on retry"
```

---

### Task 8: Make CI actually install and run the tests

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/alembic.ini`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Reproduce the install failure**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
python -m pip install -e "./backend[dev]" 2>&1 | tail -5
```
Expected: `error: Multiple top-level packages discovered in a flat-layout: ['app', 'worker', 'prompts', 'alembic']`.

- [ ] **Step 2: Add explicit package discovery to `pyproject.toml`**

In `backend/pyproject.toml` add:
```toml
[tool.setuptools.packages.find]
include = ["app*", "worker*"]
```

- [ ] **Step 3: Sync runtime deps so imports resolve in CI**

The app imports `pyjwt`, `bcrypt`, `email-validator`, `slowapi`, `openai`, `pinecone-client`, `jsonschema`, etc., which live only in `requirements.txt`. Either add them to `[project.dependencies]` in `pyproject.toml`, or (simpler) change CI to install requirements. Prefer the CI change in Step 5.

- [ ] **Step 4: Fix the Alembic `script_location` cwd bug**

In `backend/alembic.ini`, change:
```ini
script_location = alembic
```
to:
```ini
script_location = %(here)s/alembic
```
so `alembic -c backend/alembic.ini upgrade head` works from the repo root.

- [ ] **Step 5: Update CI to install requirements and run from the right cwd**

In `.github/workflows/ci.yml`, replace the install line `python -m pip install -e "./backend[dev]"` with:
```yaml
      - run: python -m pip install -e "./backend[dev]" -r backend/requirements.txt
```
and ensure the test step is `PYTHONPATH=backend python -m pytest -p no:rerunfailures backend/tests -q`. Verify the `alembic upgrade head` step uses `-c backend/alembic.ini` (now fixed by Step 4).

- [ ] **Step 6: Verify locally**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
python -m pip install -e "./backend[dev]" -r backend/requirements.txt 2>&1 | tail -3
PYTHONPATH=backend python -m pytest -p no:rerunfailures backend/tests -q 2>&1 | tail -5
```
Expected: install succeeds; tests collected and pass.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/alembic.ini .github/workflows/ci.yml
git commit -m "ci: fix package discovery, alembic path, and dependency install so tests run"
```

---

### Task 9: Sanitize generated blog HTML before render (stored XSS)

**Files:**
- Modify: `frontend/package.json` (add `isomorphic-dompurify`)
- Modify: `frontend/app/brands/[id]/blogs/[blogId]/page.tsx:277`
- Create: `frontend/lib/sanitize.ts`

- [ ] **Step 1: Add the sanitizer dependency**

```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
npm install isomorphic-dompurify
```

- [ ] **Step 2: Create a strict sanitizer helper**

Create `frontend/lib/sanitize.ts`:
```ts
import DOMPurify from "isomorphic-dompurify";

export function sanitizeArticleHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      "p", "br", "h1", "h2", "h3", "h4", "ul", "ol", "li", "blockquote",
      "strong", "em", "a", "img", "figure", "figcaption", "table", "thead",
      "tbody", "tr", "th", "td", "code", "pre", "hr",
    ],
    ALLOWED_ATTR: ["href", "src", "alt", "title", "target", "rel"],
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed"],
    FORBID_ATTR: ["onerror", "onload", "onclick"],
  });
}
```

- [ ] **Step 3: Use it at the render site**

In `frontend/app/brands/[id]/blogs/[blogId]/page.tsx`, import the helper and change line 277 from:
```tsx
dangerouslySetInnerHTML={{ __html: draft.html_content }}
```
to:
```tsx
dangerouslySetInnerHTML={{ __html: sanitizeArticleHtml(draft.html_content) }}
```

- [ ] **Step 4: Verify the build and a payload test**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
npm run build 2>&1 | tail -5
node -e "const {sanitizeArticleHtml}=require('./lib/sanitize.ts'); " 2>/dev/null || \
  node --input-type=module -e "import('isomorphic-dompurify').then(m=>console.log(m.default.sanitize('<img src=x onerror=alert(1)>')))"
```
Expected: build succeeds; the `onerror` attribute is stripped from the sanitized output.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/lib/sanitize.ts "frontend/app/brands/[id]/blogs/[blogId]/page.tsx"
git commit -m "security: sanitize AI-generated blog HTML before render to prevent stored XSS"
```

---

### Task 10: Stop storing tokens in localStorage; harden cookie and JSON.parse

**Files:**
- Modify: `frontend/lib/auth.ts:8-41`

- [ ] **Step 1: Stop persisting the refresh token in localStorage and harden the cookie**

In `frontend/lib/auth.ts` `saveSession` (lines 8-31): remove `localStorage.setItem(REFRESH_TOKEN_KEY, ...)`. Keep the access token only in memory or a short-lived cookie. Change the cookie write at line 14 to include `Secure`:
```ts
const secure = location.protocol === "https:" ? "; Secure" : "";
document.cookie = `${ACCESS_TOKEN_KEY}=${data.access_token}; path=/; max-age=900; SameSite=Lax${secure}`;
```
(Full `HttpOnly` handling requires the backend/route-handler to set the cookie — tracked in Task 11. This step removes the long-lived refresh token from JS-readable storage, which is the XSS-exfiltration target, and adds `Secure`.)

- [ ] **Step 2: Guard `JSON.parse` of stored user/org**

In `getStoredUser`/`getStoredOrg` (lines 33-41), wrap the parse:
```ts
export function getStoredUser(): UserOut | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserOut;
  } catch {
    clearSession();
    return null;
  }
}
```
Apply the same pattern to `getStoredOrg`.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/auth.ts
git commit -m "security: remove refresh token from localStorage, add Secure cookie, guard JSON.parse"
```

---

### Task 11: Route all client API calls through the same-origin proxy

**Files:**
- Modify: `frontend/lib/api.ts:36-42`, `frontend/lib/auth.ts:52`, `frontend/context/AuthContext.tsx:16`, `frontend/components/TermsGuard.tsx:7`, `frontend/app/brands/[id]/review/page.tsx:24`, `frontend/app/brands/[id]/calendar/page.tsx:38`, `frontend/app/brands/[id]/onboarding/page.tsx:27`

- [ ] **Step 1: Make the client branch use relative `/api/...` URLs**

In `frontend/lib/api.ts`, the client (browser) branch must call the same-origin proxy, not `getBackendBaseUrl()`. Replace the `http://localhost:8000` fallback usage so that when running in the browser the base is `""` (relative) and requests go to `/api/v1/...`. Keep `getBackendBaseUrl()` server-only (used by the route handler and server components).

- [ ] **Step 2: Remove the `localhost:8000` fallback from client-imported modules**

In each of `frontend/lib/auth.ts:52`, `frontend/context/AuthContext.tsx:16`, `frontend/components/TermsGuard.tsx:7`, and the three `brands/[id]/*` pages, replace:
```ts
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
```
with a relative base for browser calls:
```ts
const BACKEND = ""; // same-origin: requests hit the /api/* proxy
```
and prefix paths with `/api` (e.g. `fetch("/api/v1/auth/me", ...)`). This keeps the bearer token server-side and avoids mixed-content/CORS in production.

- [ ] **Step 3: Verify no client bundle references localhost**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr/frontend
npm run build 2>&1 | tail -3
grep -rn "localhost:8000" app context components lib || echo "no localhost refs remaining"
```
Expected: build succeeds; no remaining client-side `localhost:8000`.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/auth.ts frontend/context/AuthContext.tsx frontend/components/TermsGuard.tsx "frontend/app/brands/[id]/review/page.tsx" "frontend/app/brands/[id]/calendar/page.tsx" "frontend/app/brands/[id]/onboarding/page.tsx"
git commit -m "fix: route client API calls through same-origin proxy, drop localhost fallback"
```

---

### Task 12: Stop redirecting authenticated users away from informational pages

**Files:**
- Modify: `frontend/middleware.ts:3,18-22`

- [ ] **Step 1: Narrow the auto-redirect to auth-only pages**

In `frontend/middleware.ts`, the block at 18-22 redirects authenticated users away from every `PUBLIC_PATHS` entry, including `/terms`, `/privacy`, and `/verify-email`. Introduce a separate set for pages that should bounce signed-in users:
```ts
const AUTH_ONLY_PATHS = ["/login", "/signup"];
...
if (token && AUTH_ONLY_PATHS.includes(url.pathname)) {
  url.pathname = "/brands";
  return NextResponse.redirect(url);
}
```
Leave `/terms`, `/privacy`, `/verify-email` reachable while logged in (TermsGuard links to `/terms` in a new tab that carries the auth cookie).

- [ ] **Step 2: Verify build and the terms path**

Run: `cd frontend && npm run build 2>&1 | tail -3`
Expected: build succeeds. Manually confirm logged-in navigation to `/terms` is not redirected (preview server or unit test of the matcher logic).

- [ ] **Step 3: Commit**

```bash
git add frontend/middleware.ts
git commit -m "fix: allow authenticated users to view /terms, /privacy, /verify-email"
```

---

## P2 — Defense-in-depth and correctness

### Task 13: Fix CORS to suffix/host match and gate dev origins

**Files:**
- Modify: `backend/app/main.py:38-70`

- [ ] **Step 1: Replace substring origin matching with parsed-host suffix check**

In `backend/app/main.py`, the `NgrokCORSMiddleware` uses `".ngrok.io" in origin`, which matches `https://evil.ngrok.io.attacker.com`. Replace with a parsed-host check and only register dev origins in development:
```python
from urllib.parse import urlparse

_NGROK_SUFFIXES = (".ngrok.io", ".ngrok.app", ".ngrok-free.app")

def _origin_allowed(origin: str, app_env: str) -> bool:
    try:
        host = urlparse(origin).hostname or ""
    except ValueError:
        return False
    if app_env == "development":
        if host == "localhost" or host == "127.0.0.1":
            return True
        if any(host == s.lstrip(".") or host.endswith(s) for s in _NGROK_SUFFIXES):
            return True
    return origin in settings.allowed_origins  # explicit prod allowlist
```
Use `_origin_allowed(origin, settings.app_env)` in the middleware, and only reflect the origin + set `Access-Control-Allow-Credentials: true` when it returns `True`. Add an `allowed_origins: list[str] = []` field to `Settings` for the production allowlist.

- [ ] **Step 2: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py backend/app/config.py
git commit -m "security: CORS host-suffix match and dev-only origin gating"
```

---

### Task 14: Rate-limit auth endpoints and remove login timing leak

**Files:**
- Modify: `backend/app/main.py` (wire `slowapi` Limiter)
- Modify: `backend/app/routers/auth.py:201-206`

- [ ] **Step 1: Wire a slowapi Limiter on the app**

`slowapi` is already in `requirements.txt`. In `backend/app/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 2: Decorate login/signup/resend**

In `backend/app/routers/auth.py`, add `@limiter.limit("5/minute")` to `login`, `signup`, and `resend_verification` (import the shared `limiter`; the route functions must accept `request: Request`).

- [ ] **Step 3: Remove the user-enumeration timing leak**

At `backend/app/routers/auth.py:206`, always run a bcrypt comparison even when the user is absent so timing is uniform:
```python
from app.auth.password import verify_password, DUMMY_HASH  # precomputed bcrypt hash
...
if user is None:
    verify_password(payload.password, DUMMY_HASH)  # constant-time dummy
    raise HTTPException(status_code=401, detail="Invalid credentials")
if not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=401, detail="Invalid credentials")
```
Add `DUMMY_HASH = bcrypt.hashpw(b"x", bcrypt.gensalt()).decode()` (computed once) to `backend/app/auth/password.py`.

- [ ] **Step 4: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/routers/auth.py backend/app/auth/password.py
git commit -m "security: rate-limit auth endpoints and remove login timing oracle"
```

---

### Task 15: Block SSRF in connection-test endpoints and unblock the event loop

**Files:**
- Modify: `backend/app/routers/publishing.py:298-329`
- Modify: `backend/app/routers/integrations.py:331-391`

- [ ] **Step 1: Validate target URLs with the Task-6 guard**

In both `test_publisher_connection` (publishing.py) and `test_webhook_config` (integrations.py), call `assert_public_url(target_url)` (from `app.services.url_guard`) on the user-supplied URL/config before any network call; return HTTP 400 on `UnsafeURLError`.

- [ ] **Step 2: Run the synchronous network call off the event loop**

`publisher.test_connection()` is a blocking call inside an `async def`. Wrap it:
```python
from starlette.concurrency import run_in_threadpool
result = await run_in_threadpool(publisher.test_connection)
```

- [ ] **Step 3: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/publishing.py backend/app/routers/integrations.py
git commit -m "security: block SSRF in connection-test endpoints and offload blocking calls"
```

---

### Task 16: Org-scope the publishing health endpoint

**Files:**
- Modify: `backend/app/routers/publishing.py:332-369`

- [ ] **Step 1: Add the org filter**

`get_publishing_health` queries `PublishingQueue` with no `org_id` filter (every other endpoint in the file scopes by `Brand.org_id == current_user.org_id`). Join `BlogSchedule` → `Brand` and add `.where(Brand.org_id == current_user.org_id)` to the stuck-job and failure-rate queries. (This depends on Task 5 having fixed the `func.case` crash in the same function.)

- [ ] **Step 2: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/publishing.py
git commit -m "security: org-scope publishing health to prevent cross-tenant leak"
```

---

### Task 17: Lock down the Next.js API proxy

**Files:**
- Modify: `frontend/app/api/[...path]/route.ts:20-45`

- [ ] **Step 1: Require auth, allowlist the path prefix, and forward a curated header set**

In `frontend/app/api/[...path]/route.ts`:
```ts
const segments = path; // string[]
if (segments[0] !== "v1") {
  return new Response("Not found", { status: 404 });
}
const token = request.cookies.get("100xai_access_token")?.value;
if (!token) {
  return new Response("Unauthorized", { status: 401 });
}
const headers = new Headers();
const ct = request.headers.get("content-type");
if (ct) headers.set("content-type", ct);
const accept = request.headers.get("accept");
if (accept) headers.set("accept", accept);
headers.set("authorization", `Bearer ${token}`);
```
Do not forward the inbound `cookie` or client `authorization` header upstream. This closes the unauthenticated full-backend exposure (`/api/docs`, `/api/openapi.json`, admin routers) through the trusted frontend origin.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -3`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/api/[...path]/route.ts"
git commit -m "security: require auth and allowlist paths in Next.js API proxy"
```

---

### Task 18: Stop persisting fabricated keyword metrics as real data

**Files:**
- Modify: `backend/app/services/seo_research.py:633-730,1092-1096`

- [ ] **Step 1: Flag estimated metrics instead of presenting them as measured**

When DataForSEO is unavailable and SerpAPI is the source, `_estimate_search_volume`/`_estimate_keyword_difficulty`/`_estimate_cpc` produce `random.randint`-based numbers (`seo_research.py:649-730`). In `serpapi_fetch_related_keywords` (633-644) and `run_keyword_research` (1092-1096): set the real metric columns to `None` when no real provider supplied them, and add/set a `source="estimated"` (or `metrics_estimated=True`) field. Exclude estimated rows from `score_keywords` ranking and from the AI primary-keyword selection, or weight them to zero. Surface the `source` to the frontend so estimates are labeled.

- [ ] **Step 2: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/seo_research.py
git commit -m "fix: do not persist random-estimated keyword metrics as real SEO data"
```

---

## P3 — Low-severity hardening

### Task 19: Parse sitemaps with defusedxml

**Files:**
- Modify: `backend/app/services/crawler.py:123`
- Modify: `backend/requirements.txt` (add `defusedxml`)

- [ ] **Step 1: Add dependency and swap the parser**

Add `defusedxml` to `backend/requirements.txt`. In `crawler.py`, replace `from xml.etree import ElementTree` / `ElementTree.fromstring(resp.text)` (line 123) with:
```python
from defusedxml.ElementTree import fromstring as safe_fromstring
...
root = safe_fromstring(resp.text)
```
Also cap the response size before parsing (reject sitemaps over, e.g., 5 MB).

- [ ] **Step 2: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/crawler.py backend/requirements.txt
git commit -m "security: parse sitemaps with defusedxml and cap response size"
```

---

### Task 20: Make Razorpay webhook idempotency concurrency-safe

**Files:**
- Modify: `backend/app/services/billing.py:118-160`

- [ ] **Step 1: Treat the unique-constraint violation as already-processed**

In `handle_event`, wrap the insert/commit so a duplicate `razorpay_event_id` (unique constraint at `models/billing.py:30`) under concurrent delivery returns success instead of a 500:
```python
from sqlalchemy.exc import IntegrityError
try:
    db.add(WebhookEvent(razorpay_event_id=event_id, ...))
    db.commit()
except IntegrityError:
    db.rollback()
    return  # already processed by a concurrent delivery
```

- [ ] **Step 2: Run the suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests -q`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/billing.py
git commit -m "fix: make Razorpay webhook idempotency concurrency-safe"
```

---

### Task 21: Add pagination to the keywords list

**Files:**
- Modify: `frontend/app/brands/[id]/keywords/page.tsx:420`

- [ ] **Step 1: Replace the hard `slice(0, 20)` with real pagination**

`listKeywords(brandId)` already supports `limit`/`offset` and returns `total`, but the UI renders `keywords.slice(0, 20)`. Wire offset-based "Load more" (or page controls) to the existing params and render the load error in the UI instead of only `console.error`.

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | tail -3`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/brands/[id]/keywords/page.tsx"
git commit -m "fix: paginate keywords list so all rows are reachable"
```

---

### Task 22: Use server_default on NOT NULL columns in migration 0009

**Files:**
- Modify: `backend/alembic/versions/20260607_0009_blog_scheduling_tables.py:30,37-39,46-48`
- Modify: `backend/app/models/schedule.py:125` (align nullability)

- [ ] **Step 1: Replace Python `default=` with DB-level `server_default`**

In `20260607_0009_blog_scheduling_tables.py`, `default=` on `op.create_table` columns is a no-op at the DB level. Change e.g.:
```python
sa.Column("target_channels", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
```
for each NOT NULL column that had a Python `default=`. Also reconcile the drift: migration makes `schedule_templates.content_type` nullable while the model maps it NOT NULL (`models/schedule.py:125`) — pick one and make them match (recommend NOT NULL with a `server_default`).

- [ ] **Step 2: Verify the migration applies cleanly**

Run:
```bash
cd /Users/shubhamrathod/Downloads/pr
alembic -c backend/alembic.ini upgrade head 2>&1 | tail -5
```
Expected: upgrade succeeds (uses the Task-8 alembic path fix).

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/20260607_0009_blog_scheduling_tables.py backend/app/models/schedule.py
git commit -m "fix: use server_default on NOT NULL scheduling columns; align model nullability"
```

---

## Self-Review

**Spec coverage:** All 29 inventory rows map to a task (T1–T22; several rows share a task — e.g. the two SSRF-test endpoints in T15, the four infra/secret items in T1/T2). No audit finding is unaddressed.

**Placeholder scan:** Every code step includes concrete code or exact commands. Operator-only actions (credential rotation, setting prod env vars) are explicitly called out as such because they cannot be done by editing code — these are not placeholders but required human steps.

**Type/name consistency:** `assert_public_url` / `UnsafeURLError` (defined in T6) are reused by name in T15. `sanitizeArticleHtml` (T9) used at its single call site. `DUMMY_HASH` (T14) defined in `password.py` and imported in `auth.py`. The SQLAlchemy 2.0 `case(...)` positional form (T5) is used consistently and is what T16 depends on.

**Ordering note:** T6 must precede T15 (shared `url_guard`). T8 (alembic path) must precede T22's migration verification. T5 must precede T16 (same function). Otherwise tasks are independent and can be parallelized by area (backend vs frontend vs infra).

**Known limitation:** Several line numbers reference files the audit subagents read but that this session did not re-open line-by-line (e.g. `seo_research.py`, `scheduler.py` exact bounds). The implementing engineer should confirm the surrounding code before editing — the bug descriptions and code excerpts are quoted from the audit and verified for the spot-checked files (publishing.py, brands.py, config.py, the credential files, docker/.dockerignore).
