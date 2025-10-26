#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
mkdir -p data/backups data/qdrant data/postgres
 echo "Initializing default admin if set via env..."
# Stack up
docker compose up -d
echo "Stack started. Visit docs at http://localhost:8020 if docs service is running."
