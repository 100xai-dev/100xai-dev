# Merge `feat/superadmin` into `feat/email-verification-razorpay-terms`

**Date:** 2026-06-25
**Goal:** Combine the platform-superadmin feature into the email-verification branch and deploy it to the server **without breaking the running application** — specifically without breaking login.

## Context

Two feature branches share a common ancestor at `4b0bdf0` (a superadmin *docs* commit):

- `feat/superadmin` — +17 commits implementing the platform superadmin: a DB migration, auth/rbac/deps changes, a `/superadmin` router + service, a seed script, and frontend pages.
- `feat/email-verification-razorpay-terms` — +2 commits: the pinecone package rename and the docker-compose loopback/healthcheck fix. This is the branch currently deployed on the server.

### Merge surface

Of the 29 files `feat/superadmin` changes, **28 do not overlap** with the email-verification branch. There is exactly **one conflict**:

- `backend/requirements.txt`, on the single `pinecone` line. Both branches made the *same* rename (`pinecone-client>=3.2.0` → `pinecone>=5.0.0`); the email-verification side added a trailing explanatory comment. **Resolution: keep the email-verification (commented) version** — it is semantically identical to superadmin's.

## Decision: merge strategy — Approach A (merge commit)

Run `git merge feat/superadmin` into `feat/email-verification-razorpay-terms`, resolve the one conflict, and commit a merge commit.

Rejected alternatives:
- **Rebase** — would rewrite a branch that is already pushed and deployed, requiring a force-push. No upside here.
- **Cherry-pick** — duplicates 17 commits, messier history, larger conflict surface.

Approach A is the only option that does not force-push a deployed branch.

## Why the merge is runtime-safe

The superadmin branch makes two behavioral changes that *could* break a live system if mis-sequenced:

1. **New migration `20260619_0014_superadmin.py`** adds `organizations.status` and `users.disabled`. The new SQLAlchemy models reference these columns, so if the new code serves traffic before the migration runs, every query touching users/orgs fails → total login breakage.
2. **Login/refresh gating** now blocks `suspended` organizations and `disabled` users.

Both are safe because:
- The migration is **purely additive** with server defaults (`status="active"`, `disabled=false`). Existing rows get valid values; old code ignores the new columns, so the migration can run *before* the new code is swapped in.
- After migration, no existing org is `suspended` and no existing user is `disabled`, so the new gating locks nobody out.
- The `superadmin` role **satisfies every existing role gate**, so no current permission check regresses.

The key ordering rule: **run the migration before swapping in the new code.**

## Deploy runbook

### Local (produce the merged branch)
1. `git checkout feat/email-verification-razorpay-terms`
2. `git merge feat/superadmin`
3. Resolve `backend/requirements.txt` → keep `pinecone>=5.0.0  # renamed from pinecone-client ...`
4. Run the backend test suite (incl. superadmin tests) and confirm green.
5. Commit the merge and `git push`.

### Server (deploy without breakage)
Migrations are applied **manually via alembic** (no auto-run on container start).

6. `git pull` on `feat/email-verification-razorpay-terms`.
7. Set in `backend/.env`:
   - `SUPERADMIN_EMAILS=<operator-provided, comma-separated>` *(value supplied by the user at deploy time)*
   - optionally `SUPERADMIN_PASSWORD=<shared bootstrap password>` — if omitted, the seed prints a generated password once.
8. Build new images while the old ones keep running: `docker compose build api worker frontend`.
9. Run the migration with the new image (old code still serving, unaffected): `docker compose run --rm api alembic upgrade head`.
10. Swap in the new code: `docker compose up -d`.
11. Seed superadmins: `docker compose exec api python -m app.scripts.seed_superadmins`.
12. Verify (see below).

## Verification / success criteria

- Backend test suite passes locally before push (superadmin + acting-context + verification tests).
- `docker compose ps` shows api/worker/frontend healthy after deploy.
- An **existing** non-superadmin user can still log in (gating did not lock anyone out).
- The seeded superadmin account can log in and reach `/superadmin`.
- `alembic current` reports revision `20260619_0014`.

## Open items / risks

- **SUPERADMIN_EMAILS value** is provided by the operator at deploy time; not baked into the spec.
- If `alembic upgrade head` fails in the container (e.g. alembic config/path), fall back to running it from the backend working directory inside the container; confirm `alembic current` before and after.
- This spec covers the merge + deploy only. It does **not** re-audit the superadmin feature's own correctness (its tests are assumed authoritative).
