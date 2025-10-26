#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${DB_URL:-}" ]]; then
  echo "DB_URL is required in environment" >&2
  exit 0
fi
psql "$DB_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS cirs;
-- Placeholder: apply migrations when defined
SQL
