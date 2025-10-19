## 2025-10-19 — Milestone 2.5: Unified Transcription & Validation (ASR GPU service)
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/transcription/asr_gpu/main.py  
- backend/transcription/asr_gpu/config.py  
- backend/transcription/asr_gpu/requirements.txt  
- backend/transcription/asr_gpu/Dockerfile  

**Actions Completed:**  
- Implemented GPU WhisperX-based ASR with optional Pyannote diarization.  
- Added media detection (audio/video) and ffmpeg-based audio extraction.  
- Outputs versioned transcripts under `/data/transcripts/{audio|videos}/versions/<timestamp>/`.  
- JSON sidecars include `start_time`, `end_time`, `speaker`, `text`, `confidence`.  
- Resumability via sha256 index at `/data/transcripts/.processed_index.json`.  
- Optional Postgres write guarded by `--source-id` and `DB_URL` (FK must exist).  
- Dockerfile for CUDA 12.1 runtime; installs torch (cu121), whisperx, faster-whisper, ffmpeg.  

**Verification:**  
- Basic run: `python backend/transcription/asr_gpu/main.py --input /data/ingestion` scans and processes media.  
- Sidecar `.json` and `.txt` emitted to versioned directories.  
- Diarization toggled via `.env` (`ASR_DIARIZATION=true`) with `PYANNOTE_AUTH_TOKEN`.  

**Next Step:**  
- Integrate DB writes with real `source_id` from ingestion catalog.  
- Add docker-compose service `asr_gpu` with GPU (`--gpus all`).  
- Hook validation pipeline (medical lexicon) per Planning.md Section 6.  

## 2025-10-19 — Milestone 2.6: Medical Validation & Correction Pipeline
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/processing/validation_gpu/config.py  
- backend/processing/validation_gpu/requirements.txt  
- backend/processing/validation_gpu/main.py  
- backend/processing/validation_gpu/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented `validation_gpu` service to scan ASR sidecars under `/data/transcripts/.../versions/`.  
- Validates and corrects medical terms; assigns `confidence_medical` and `confidence_contextual` per segment.  
- Outputs validated JSON to `/data/validated/{audio|videos}/<run_tag>/<file>.json`.  
- Optional DB update to `cirs.transcripts` (updates `full_text`, `quality_metrics`, `validation_version`).  
- Resumability via `/data/validated/.validated_index.json`.  
- Added service to `docker-compose.yml` with GPU reservation support.  

**Verification:**  
- Local run: `python backend/processing/validation_gpu/main.py --input /data/transcripts` produced validated outputs under `/data/validated/...`.  
- Compose build: `docker compose up -d --build validation_gpu` starts the service (GPU optional).  
- Summary logs report files processed, segment counts, and corrected segments.  

**Next Step:**  
- Expand medical vocab and entity linking with SciSpaCy/MedSpaCy + UMLS loaders.  
- Integrate with Milestone 2.7 (Chunking & Embeddings) to consume validated outputs.  
- Add stricter schema validation and unit tests for correction rules.  

## 2025-10-19 — Milestone 2.7: Chunking & Embeddings GPU Service
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/processing/chunking_embeddings_gpu/config.py  
- backend/processing/chunking_embeddings_gpu/chunker.py  
- backend/processing/chunking_embeddings_gpu/embedder.py  
- backend/processing/chunking_embeddings_gpu/main.py  
- backend/processing/chunking_embeddings_gpu/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented chunking service to segment validated transcripts into coherent chunks with overlap.  
- Implemented GPU embeddings using `sentence-transformers` (model configurable via `EMBED_MODEL`).  
- Upserts vectors and payload to Qdrant collection (`cirs_chunks_v1` by default).  
- Optional Postgres writes to `cirs.chunks` and `cirs.embeddings` for lineage.  
- Resumability via `/data/chunks/.embedded_index.json`.  

**Verification:**  
- Local run: `python backend/processing/chunking_embeddings_gpu/main.py --input /data/validated` produced chunk JSON under `/data/chunks/<run_tag>/` and upserted to Qdrant.  
- Compose: `docker compose up -d --build chunking_embeddings_gpu` starts the service (GPU reserved).  
- Summary logs include files processed, chunk count, model name, batch size, and Qdrant collection.  

**Next Step:**  
- Add topic/entity tagging; integrate with SciSpaCy/MedSpaCy output.  
- Ensure `source_id` propagation from ingestion/ASR → validation → chunking for full provenance.  
- Proceed to Milestone 2.8 – Hybrid Retrieval API (RAG Core).  

## 2025-10-19 — Milestone 2.8: Hybrid Retrieval API (RAG Core)
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/retrieval/hybrid_retriever/config.py  
- backend/retrieval/hybrid_retriever/vector.py  
- backend/retrieval/hybrid_retriever/lexical.py  
- backend/retrieval/hybrid_retriever/main.py  
- backend/retrieval/hybrid_retriever/requirements.txt  
- backend/retrieval/hybrid_retriever/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented FastAPI service with `/search`, `/rebuild-index`, and `/health`.  
- Vector search via Qdrant using the same embedding model as chunking (`EMBED_MODEL`).  
- Lexical BM25 index built from `/data/chunks/...` via Whoosh; `/rebuild-index` endpoint populates it.  
- Hybrid fusion using weighted RRF (`VECTOR_WEIGHT`, `LEXICAL_WEIGHT`), dedup + re-rank.  
- Added `qdrant` service to Compose with local storage at `./data/qdrant`.  

**Verification:**  
- Compose: `docker compose up -d --build qdrant hybrid_retriever` runs API at `http://localhost:8002`.  
- Index build: `curl -X POST http://localhost:8002/rebuild-index` reports documents added.  
- Search: `curl "http://localhost:8002/search?q=neuroinflammation&mode=hybrid"` returns ranked results with payload fields (`source_id`, `start_time`, `topic_tags`, etc.).  

**Next Step:**  
- Add lexical fallback when Qdrant unavailable; expose `/metrics` for latency.  
- Thread `source_id` through earlier stages for complete provenance in payloads.  
- Proceed to Milestone 2.9 – Chat Orchestrator & Curriculum Builder Integration.  

## 2025-10-19 — Milestone 2.9: Chat Orchestrator & Curriculum Builder Integration
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/chat_orchestrator/config.py  
- backend/chat_orchestrator/llm_client.py  
- backend/chat_orchestrator/orchestrator.py  
- backend/chat_orchestrator/curriculum_builder.py  
- backend/chat_orchestrator/main.py  
- backend/chat_orchestrator/requirements.txt  
- backend/chat_orchestrator/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented Chat Orchestrator FastAPI with `/chat`, `/module`, `/health`.  
- Integrated Hybrid Retriever for context; grounded prompts with inline citation schema.  
- LLM client supports local (Ollama) and remote (OpenAI-compatible) modes via `.env`.  
- Basic Curriculum Builder converts retrieved chunks into module JSON.  
- Compose service `chat_orchestrator` exposed at `http://localhost:8003`.  

**Verification:**  
- Compose: `docker compose up -d --build chat_orchestrator` launches API.  
- Chat: `curl -X POST localhost:8003/chat -H "Content-Type: application/json" -d '{"query":"What are symptoms of CIRS?"}'` returns grounded answer JSON with citations.  
- Module: `curl -X POST localhost:8003/module -H "Content-Type: application/json" -d '{"topic":"Lyme co-infections"}'` returns module JSON.  

**Next Step:**  
- Add guardrails (citation enforcement, answer confidence scoring) and `/metrics` endpoint.  
- Add Markdown export to `/module?format=md` and richer objectives/quizzes.  
- Wire deterministic seeds and temperature in `.env`; add retries/fallbacks if retriever/LLM unavailable.  

## 2025-10-19 — Milestone 3.0: Frontend Chat UI & Curriculum Builder Interface
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- frontend/chat_ui/package.json  
- frontend/chat_ui/vite.config.ts  
- frontend/chat_ui/index.html  
- frontend/chat_ui/src/main.tsx  
- frontend/chat_ui/src/App.tsx  
- frontend/chat_ui/src/lib/api.ts  
- frontend/chat_ui/src/components/ChatPanel.tsx  
- frontend/chat_ui/src/components/MessageBubble.tsx  
- frontend/chat_ui/src/components/CitationViewer.tsx  
- frontend/chat_ui/src/components/ModuleBuilder.tsx  
- frontend/chat_ui/src/components/SettingsDrawer.tsx  
- frontend/chat_ui/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Scaffolded Vite React TS app with chat and learning mode tabs.  
- Implemented chat panel calling `/chat` and module builder calling `/module`.  
- Added basic message rendering with citations and a settings drawer reflecting env defaults.  
- Dockerized UI and added `ui_web` service exposed at `http://localhost:5173`.  

**Verification:**  
- Build UI image: `docker compose up -d --build ui_web` serves app at `http://localhost:5173`.  
- Chat request hits `chat_orchestrator` and displays response + citations.  
- Module builder fetches from `/module` and renders objectives/sections/quiz.  

**Next Step:**  
- Add Tailwind + shadcn/ui styling, SSE streaming, and citation preview modals.  
- Link citations to transcript viewer routes (`/transcript?source_id=...&t=...`).  
- Add Markdown export button for modules and basic state persistence.  

## 2025-10-19 — Milestone 3.1: Provenance Dashboard & Monitoring Suite
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/monitoring/config.py  
- backend/monitoring/metrics_collector.py  
- backend/monitoring/provenance.py  
- backend/monitoring/main.py  
- backend/monitoring/requirements.txt  
- backend/monitoring/Dockerfile  
- frontend/monitoring_ui/package.json  
- frontend/monitoring_ui/vite.config.ts  
- frontend/monitoring_ui/index.html  
- frontend/monitoring_ui/src/main.tsx  
- frontend/monitoring_ui/src/App.tsx  
- docker-compose.yml  

**Actions Completed:**  
- Implemented Monitoring API with `/health`, `/metrics` (Prometheus), `/provenance/{answer_id}`, and `/reprocess/{source_id}` (stub queue).  
- Added minimal provenance resolver and Prometheus metrics collectors.  
- Built Monitoring UI (React/Vite) with metric cards and a simple provenance list.  
- Added `monitoring` and `monitoring_ui` services to Compose (ports 8010 and 5174).  

**Verification:**  
- Compose: `docker compose up -d --build monitoring monitoring_ui` exposes API at `http://localhost:8010` and UI at `http://localhost:5174`.  
- `curl http://localhost:8010/metrics` returns Prometheus metrics text.  
- `curl -X POST http://localhost:8010/provenance/demo -H "Content-Type: application/json" -d '{"retrieved":[]}'` returns a provenance skeleton.  

**Next Step:**  
- Integrate real lineage from Postgres + Qdrant payloads; include run tags and exact file links.  
- Add GPU utilization exporters and LLM latency hooks from services.  
- Optional: Add Prometheus + Grafana stack; wire scrape target at `/metrics`.  

## 2025-10-19 — Milestone 3.2: LLM Evaluation & Confidence Scoring Layer
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/evaluation/config.py  
- backend/evaluation/similarity.py  
- backend/evaluation/scorer.py  
- backend/evaluation/validator.py  
- backend/evaluation/main.py  
- backend/evaluation/requirements.txt  
- backend/evaluation/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented Evaluation API with `/evaluate`, `/history`, and `/metrics`.  
- Confidence scoring via embedding cosine similarity (answer vs retrieved chunks).  
- Support ratio using n-gram overlap; hallucination risk from confidence and citation density.  
- Medical grounding validator placeholder to flag terms missing from context.  
- Optional Postgres upsert to `cirs.answer_evaluations`.  

**Verification:**  
- Compose: `docker compose up -d --build evaluation` exposes API at `http://localhost:8011`.  
- Health/Metrics: `curl http://localhost:8011/health` and `curl http://localhost:8011/metrics`.  
- Evaluate sample: `curl -X POST http://localhost:8011/evaluate -H "Content-Type: application/json" -d '{"answer_id":"demo","answer_text":"...","citations":[],"retrieved_chunks":[{"text":"..."}]}'`.  

**Next Step:**  
- Wire Chat Orchestrator to call `/evaluate` and surface confidence badges in `/chat` response.  
- Replace validator with SciSpaCy/MedSpaCy + UMLS; add unit tests for scoring.  
- Expose aggregated evaluation metrics in Monitoring dashboard (3.1).

## 2025-10-19 — Milestone 3.3: Evidence Alignment & Summarization QA
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/alignment_qa/config.py  
- backend/alignment_qa/aligner.py  
- backend/alignment_qa/summarizer.py  
- backend/alignment_qa/main.py  
- backend/alignment_qa/requirements.txt  
- backend/alignment_qa/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented sentence-level alignment: splits answers into sentences, computes semantic similarity to retrieved chunks, and maps sentences → evidence chunks.  
- Calculated metrics: `alignment_coverage`, `agreement_score`, and `weak_claims`.  
- Generated concise QA summary based on coverage/agreement thresholds.  
- Persisted results to Postgres table `cirs.answer_alignment` (idempotent upsert).  
- Exposed Prometheus metrics (`alignment_coverage`, `alignment_agreement`).  

**Verification:**  
- Compose: `docker compose up -d --build alignment_qa` exposes API at `http://localhost:8012`.  
- Health/Metrics: `curl http://localhost:8012/health` and `curl http://localhost:8012/metrics`.  
- Align sample:
  `curl -X POST http://localhost:8012/align -H "Content-Type: application/json" -d '{"answer_id":"demo","answer_text":"CIRS involves biotoxins. Treatment includes bile acid sequestrants.","retrieved_chunks":[{"chunk_id":"c1","text":"Biotoxin exposure is common in CIRS."},{"chunk_id":"c2","text":"Bile acid sequestrants are used as treatment options."}]}'`  

**Next Step:**  
- Integrate Chat Orchestrator to call `/align` and return per-sentence evidence with UI highlights (🟢/🟡/🔴).  
- Upgrade sentence splitter to spaCy; add configurable `ALIGNMENT_MIN_SCORE`.  
- Visualize coverage trend in Monitoring UI; add filter by `source_type`.  

## 2025-10-19 — Milestone 3.4: Adaptive Module Generation & Reinforcement Loop
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/reinforcement/config.py  
- backend/reinforcement/feedback_analyzer.py  
- backend/reinforcement/adaptive_trainer.py  
- backend/reinforcement/main.py  
- backend/reinforcement/requirements.txt  
- backend/reinforcement/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented Reinforcement API with `/reinforce`, `/status`, and `/metrics`.  
- Aggregates QA signals from `cirs.answer_evaluations` and `cirs.answer_alignment` over rolling window.  
- Computes parameter adjustments (retrieval_top_k, chunk_overlap, summary_temperature) via heuristic rules.  
- Persists runs to `cirs.model_tuning_history` (idempotent upsert).  
- Compose service `reinforcement` exposed at `http://localhost:8013`.  

**Verification:**  
- Compose: `docker compose up -d --build reinforcement` exposes API.  
- Health/Metrics: `curl http://localhost:8013/health` and `curl http://localhost:8013/metrics`.  
- Trigger run: `curl -X POST http://localhost:8013/reinforce`.  
- Check last status: `curl http://localhost:8013/status`.  

**Next Step:**  
- Wire Curriculum Builder to consume tuned params; optionally write back to `.env`/YAML.  
- Add scheduler for daily runs; chart reinforcement trends in Monitoring UI.  
- Extend adjustments with coverage/agreement thresholds and guardrails.

## 2025-10-19 — Milestone 3.5: User Feedback Loop & Model Fine-Tuning
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/feedback/config.py  
- backend/feedback/schema.py  
- backend/feedback/main.py  
- backend/feedback/requirements.txt  
- backend/feedback/Dockerfile  
- docker-compose.yml  
  - (Optional planned) backend/finetune/*  

**Actions Completed:**  
- Implemented Feedback API with `/feedback/answer`, `/feedback/module`, `/history`, and `/metrics` counters.  
- Created DB schema for `cirs.user_feedback` and `cirs.finetune_corpus`.  
- Wired Prometheus `feedback_total{type, rating}` counter increments per submission.  
- Added `feedback` service on port 8014 to Compose.  
- (Planned) Optional `finetune` service wiring added to Compose; code to be added when enabled.  

**Verification:**  
- Compose: `docker compose up -d --build feedback` exposes API at `http://localhost:8014`.  
- Post feedback: `curl -X POST http://localhost:8014/feedback/answer -H "Content-Type: application/json" -d '{"answer_id":"a1","rating":5,"helpful":true}'`.  
- Metrics: `curl http://localhost:8014/metrics` shows `feedback_total`.  

**Next Step:**  
- Integrate reinforcement (3.4) to ingest rolling feedback; expand `cirs.finetune_corpus` with high-confidence, high-coverage, high-rating samples.  
- Implement optional `backend/finetune/` LoRA trainer (PEFT) gated by `FINETUNE_ENABLED`.  
- Add UI rating controls (thumbs + 1–5) and flags in Chat and Module views.

## 2025-10-19 — Milestone 3.6: Security / PII Guardrails & License Compliance
**Model:** GPT-5 Low Reasoning  
**Files Modified:**  
- backend/security_guardrails/config.py  
- backend/security_guardrails/redactor.py  
- backend/security_guardrails/main.py  
- backend/security_guardrails/requirements.txt  
- backend/security_guardrails/Dockerfile  
- backend/license_audit/config.py  
- backend/license_audit/auditor.py  
- backend/license_audit/main.py  
- backend/license_audit/requirements.txt  
- backend/license_audit/Dockerfile  
- docker-compose.yml  

**Actions Completed:**  
- Implemented PII redaction service with `/redact`, `/audit`, `/metrics`; logs to `cirs.redaction_log` and `/data/security/redaction_log.json`.  
- Added regex-based detectors (emails, phones, MRN, person-like) with mask tokens.  
- Implemented License Audit service with `/license/scan`, `/license/report`, `/metrics`; populates `cirs.license_registry`.  
- Emitted Prometheus metrics: `pii_redactions_total{type}` and `restricted_sources_total{license}`.  
- Added `security_guardrails` (8016) and `license_audit` (8017) services to Compose.  

**Verification:**  
- Security: `docker compose up -d --build security_guardrails`; `curl -X POST http://localhost:8016/redact -H "Content-Type: application/json" -d '{"text":"John Smith email john@x.com"}'` returns masked text; `curl http://localhost:8016/metrics`.  
- License: `docker compose up -d --build license_audit`; `curl -X POST http://localhost:8017/license/scan -H "Content-Type: application/json" -d '{"path":"/data"}'`; `curl http://localhost:8017/license/report`.  

**Next Step:**  
- Thread license metadata through chunk payloads and enforce export restrictions in `chat_orchestrator`/`curriculum_builder`.  
- Optionally integrate Presidio/SpaCy for improved PII detection.  
- Add Monitoring UI “Data Integrity” tab with redactions over time and license distribution.
