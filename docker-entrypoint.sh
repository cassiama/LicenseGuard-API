#!/usr/bin/env bash
set -euo pipefail

APP_DIR=${APP_DIR:-/app}
ALEMBIC_CONFIG=${ALEMBIC_CONFIG:-$APP_DIR/alembic.ini}
cd "$APP_DIR"

# require a DB url for anything DB-related
require_db() {
    : "${DB_URL:?DB_URL is required (e.g., postgresql+asyncpg://user:pass@host:5432/db)}"
}

case "${1:-serve}" in
    migrate)
    shift
    require_db
    echo "Running Alembic migrations..."
    alembic upgrade head "$@"
    ;;
    serve)
    shift
    require_db
    echo "Starting API..."
    exec /api/.venv/bin/fastapi run src/srv/app.py --port 80 --host 0.0.0.0 "$@"
    ;;
    *)
    echo "Unknown subcommand: $1 (expected 'serve' or 'migrate')" >&2; exit 2
    ;;
esac