#!/usr/bin/env bash
set -euo pipefail
mkdir -p sbom
if ! command -v syft &>/dev/null; then
  echo "Install syft for local SBOM generation: https://github.com/anchore/syft" >&2
  exit 0
fi
IMAGES=(
  ghcr.io/OWNER/cirs-auth:latest
  ghcr.io/OWNER/cirs-backup:latest
  ghcr.io/OWNER/cirs-feedback:latest
  ghcr.io/OWNER/cirs-hybrid_retriever:latest
  ghcr.io/OWNER/cirs-chat_orchestrator:latest
  ghcr.io/OWNER/cirs-license_audit:latest
  ghcr.io/OWNER/cirs-security_guardrails:latest
)
for IMG in "${IMAGES[@]}"; do
  OUT="sbom/$(echo "$IMG" | tr '/:' '__').cdx.json"
  echo "Generating SBOM for $IMG -> $OUT"
  syft "$IMG" -o cyclonedx-json > "$OUT" || true
done
