#!/usr/bin/env sh
set -eu

cd apps/api
uvicorn ai_brand_os.main:app --reload
