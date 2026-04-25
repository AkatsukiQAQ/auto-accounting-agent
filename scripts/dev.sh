#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "→ Port $PORT in use; killing stale process(es)..."
  lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.3
fi

exec uv run uvicorn backend.api.main:app --reload --host 127.0.0.1 --port "$PORT"
