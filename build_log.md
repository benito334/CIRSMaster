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
