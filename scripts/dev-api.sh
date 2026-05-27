#!/usr/bin/env sh
set -eu

cd backend
PYTHONPATH=. uvicorn app.main:app --reload
