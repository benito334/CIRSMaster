#!/usr/bin/env bash
set -euo pipefail
VERSION_ARG=${1:-"latest"}
OWNER=${OWNER:-"OWNER"}

echo "Login to GHCR (if needed)..."
echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USERNAME:-$USER}" --password-stdin || true

echo "Pulling images for compose.prod.yml..."
docker compose -f compose.prod.yml pull || true

echo "Running migrations..."
./scripts/migrate.sh || true

echo "Starting stack..."
docker compose -f compose.prod.yml up -d

echo "Pruning old images..."
docker image prune -f || true
