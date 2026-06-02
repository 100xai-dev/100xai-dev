#!/usr/bin/env bash
# scripts/start_worker.sh
# Start the RQ worker. Credentials are loaded automatically from
# backend/.env and the root .env — no need to pass them here.

set -e

cd "$(dirname "$0")/.."  # always run from repo root

OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
PYTHONPATH=backend:. \
backend/venv/bin/rq worker \
  --with-scheduler \
  onboarding blog purge keyword_research default
