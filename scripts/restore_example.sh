#!/usr/bin/env bash
set -euo pipefail
SNAP_ID="$1"
PARTS=${2:-"pg qdrant artifacts"}
ROOT=${BACKUP_ROOT:-/backups/snapshots}
DB_URL=${DB_URL:-""}

if [[ -z "$SNAP_ID" ]]; then
  echo "Usage: $0 <snapshot_id> [\"pg qdrant artifacts\"]" >&2
  exit 1
fi

echo "Stopping write-heavy services (if any)..."
# docker compose stop chat_orchestrator hybrid_retriever ...

if [[ "$PARTS" == *"pg"* ]]; then
  if [[ -z "$DB_URL" ]]; then
    echo "DB_URL not set in environment; export it before running restore." >&2
    exit 1
  fi
  echo "Restoring Postgres from $ROOT/$SNAP_ID/pg_dump.sql.gz"
  gunzip -c "$ROOT/$SNAP_ID/pg_dump.sql.gz" | psql "$DB_URL"
fi

if [[ "$PARTS" == *"artifacts"* ]]; then
  echo "Restoring artifacts to /"
  tar -xzvf "$ROOT/$SNAP_ID/data_artifacts.tar.gz" -C /
fi

echo "Start stack and verify."
