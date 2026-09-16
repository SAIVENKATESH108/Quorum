#!/bin/sh
set -e

# Run database migrations before starting service
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "[Quorum Entrypoint] Applying database migrations (alembic upgrade head)..."
    alembic upgrade head || echo "[Quorum Entrypoint] Warning: alembic upgrade failed or skipped."
fi

# Execute CMD passed to container
exec "$@"
