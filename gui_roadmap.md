# CIRS GUI Roadmap

This document outlines the plan to make the ingestion pipeline (transcription → validation → embeddings) fully operable from the GUI, with live status/logging and review tools.

## Goals
- Run any pipeline stage (transcription, validation, embeddings) or “All” from the GUI.
- Select individual files, groups of files, or entire folders for processing.
- Live progress and robust logging with retry/cancel.
- Review transcripts and validation results, apply corrections, re-run subsets.
- RBAC for safe multi-user operations.

## Phased Plan

### Phase 0 — Foundations
- Define job and item contracts
  - Job: job_id, stage, items, status, progress, logs_path, errors, run_tag, created_by, tenant_id, options, commit_sha.
  - Item: item_id, path, type (file|folder), status, stage_status, timings, artifacts.
- Transport for live updates: Server-Sent Events (SSE) for logs and progress.
- Basic RBAC checks via Auth service and path allowlists.

### Phase 1 — Pipeline Controller (Backend)
- New FastAPI service pipeline_controller
  - POST /jobs → start job (stage, items, options)
  - GET /jobs → list jobs
  - GET /jobs/{id} → job status
  - GET /jobs/{id}/events → SSE stream (progress + logs)
  - POST /jobs/{id}/cancel
  - POST /jobs/{id}/retry
- Executors for each stage
  - Call existing CLIs (ASR → Validation → Chunk+Embed) with proper args and RUN_TAG.
  - Bounded concurrency and idempotency (respect indexes in data folders).
- Persistence (Postgres)
  - cirs.pipeline_runs, cirs.pipeline_items, cirs.pipeline_logs.
- Structured logging
  - JSON logs with job_id, item_id, stage, level, msg, ts.
  - Append plaintext /data/logs/pipeline/<job_id>.log.
- Metrics (Prometheus)
  - pipeline_jobs_total{stage,status}, pipeline_items_total{stage,status}, durations.

### Phase 2 — GUI: Run Launcher & Live Dashboard
- New “Processing” tab with pages:
  - Run Launcher: file/folder picker, stage selection, options (models, language, batch sizes, GPU toggle), submit.
  - Jobs List: filterable table of recent jobs.
  - Job Detail: overall progress, per-item status, live logs (SSE), cancel/retry, download log.
- Persist UI preferences to local storage; defaults from .env.

### Phase 3 — Reviewers: Transcript & Validation
- Transcript Viewer
  - Show segments (timestamp, speaker, text, confidence).
  - Media playback and scrubbing; edit per segment; mark as reviewed.
  - Save as new version under /data/transcripts/.../versions/<tag>.
- Validation Reviewer
  - Show segments with entities, quality_flags, and adjusted confidence.
  - Filter by flags/entity types; accept/reject flags; edit.
  - Save updated validated JSON; re-run selected items.

### Phase 4 — Quality & Resilience
- Resumability: honor .processed_index.json, .validated_index.json, .embedded_index.json.
- Retry policy with backoff; failure categories.
- Notifications: in-app toasts; optional webhook/email on job completion.

### Phase 5 — Polishing & Ops
- RBAC roles (viewer/operator/admin) for pipeline and review actions.
- Provenance: include job_id, run_tag, commit_sha in artifacts and Qdrant payloads.
- Docs: GUI pipeline guide, troubleshooting; sample presets.
- CI: smoke tests + e2e (Playwright/Cypress) for run + review.

## APIs (Draft)
- POST /jobs
  - Body: { stage, items: [{path,type}], options, run_tag }
  - Returns: { job_id }
- GET /jobs/{id}
  - Returns: { status, counts, items: [ {item_id,path,status,artifacts} ], started_at, finished_at }
- GET /jobs/{id}/events (SSE)
  - Events: progress, log, item_update, done
- POST /jobs/{id}/cancel, /retry
- GET /jobs?stage=&status=&q=

## Data Model (DDL sketch)
- cirs.pipeline_runs(job_id UUID PK, stage TEXT, status TEXT, created_by TEXT, tenant_id TEXT, options JSONB, run_tag TEXT, commit_sha TEXT, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ, counts JSONB)
- cirs.pipeline_items(job_id UUID, item_id UUID, path TEXT, type TEXT, status TEXT, stage_status JSONB, timings JSONB, artifacts JSONB, error TEXT, PRIMARY KEY(job_id, item_id))
- cirs.pipeline_logs(job_id UUID, ts TIMESTAMPTZ, level TEXT, message TEXT, item_id UUID NULL)

## Observability
- Metrics: Prometheus counters/histograms for jobs/items/durations/failures.
- Health: /health, /ready, /metrics on controller.


## Additional Features (Requested)
- Batch presets: named configurations (e.g., “Medical default”).
- GPU affinity & queueing: limit concurrent GPU jobs; per-stage GPU/CPU routing.
- Version compare: diff transcripts or validation versions.
- Export bundles: transcripts/validated/chunks packaged for external review.
- Cost/usage dashboard: tokens, GPU hours, job volumes.
- Undo/rollback of corrections via version history.
- Notes/comments: attach notes on jobs and items for collaboration.



## Acceptance Criteria
- Launch a job from the GUI, watch progress/logs in real-time, and view results.
- Review and edit transcripts/validation with versioned saves and re-run selected items.
- Metrics and logs available; RBAC enforced; jobs resilient with retry/resume.