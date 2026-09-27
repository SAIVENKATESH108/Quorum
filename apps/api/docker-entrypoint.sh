#!/bin/sh
set -e

# Default PORT to 8000 if unset or empty
export PORT="${PORT:-8000}"

# Run database migrations before starting service if DATABASE_URL is configured
if [ "$RUN_MIGRATIONS" != "false" ]; then
    if [ -n "$DATABASE_URL" ]; then
        echo "[Quorum Entrypoint] Applying database migrations (alembic upgrade head)..."
        alembic upgrade head || echo "[Quorum Entrypoint] Warning: alembic upgrade failed or skipped."
    else
        echo "[Quorum Entrypoint] Notice: DATABASE_URL is not set; skipping automatic migrations."
    fi
fi

# If no arguments provided, run default uvicorn
if [ $# -eq 0 ]; then
    exec uvicorn src.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
fi

# Execute CMD through shell so variable expansions like $PORT succeed
exec /bin/sh -c "$*"

