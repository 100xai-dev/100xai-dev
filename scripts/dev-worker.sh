#!/usr/bin/env sh
set -eu

cd apps/worker
python -m ai_brand_os_worker.main
