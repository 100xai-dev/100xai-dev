#!/usr/bin/env sh
set -eu

PYTHONPATH=backend:. python worker/main.py
