# CIRS Agent – Detailed Planning Document

> **Goal:** Build a local-first, GPU-accelerated AI system that ingests, transcribes, processes, and organizes multi-source medical content (Instagram, YouTube, PDFs, EPUBs, etc.) into structured knowledge for both retrieval (RAG) and teachable modules. Designed for modular Dockerized services and local GPU execution.

---

## ✅ Status Audit (2025-05-06)

**What is working today**

* GPU ASR CLI (`backend/transcription/asr_gpu`) produces WhisperX transcripts with diarization and optional Postgres writes.
* Validation and chunking pipelines exist and can be run as CLIs to produce validated segments and embed them into Qdrant (`backend/processing/validation_gpu`, `backend/processing/chunking_embeddings_gpu`).
* Hybrid retrieval FastAPI service (`backend/retrieval/hybrid_retriever`) provides vector/BM25/weighted results and powers the chat orchestrator.
* Chat UI + orchestrator can retrieve chunks and stream responses when the retriever + LLM endpoints are available (`frontend/chat_ui`, `backend/chat_orchestrator`).

**Major gaps discovered during review**

* All new milestone 3.x services (evaluation, alignment QA, reinforcement, feedback, monitoring, guardrails, license audit) use relative imports (e.g., `from .foo import …`) but the packages have no `__init__.py`. Running `python main.py` or `uvicorn main:app` fails immediately with `ImportError: attempted relative import with no known parent package`.【F:backend/alignment_qa/main.py†L1-L16】【F:backend/reinforcement/main.py†L1-L18】【F:backend/evaluation/main.py†L1-L19】【F:backend/feedback/main.py†L1-L11】【F:backend/security_guardrails/main.py†L1-L12】【F:backend/license_audit/main.py†L1-L12】【F:backend/monitoring/main.py†L1-L12】
* `docker-compose.yml` declares dependencies on a `db` service that does not exist and attempts to build a missing `backend/finetune` image. Bringing the stack up currently fails at the compose level.【F:docker-compose.yml†L197-L210】【be3092†L1-L2】
* No automation currently wires the ingestion outputs into the validation/chunking jobs; these are still manual CLI runs. There is also no job orchestration or scheduler.
* Monitoring/metrics references (Prometheus endpoints, provenance helpers) are mostly placeholders and have not been validated end-to-end.

**Immediate next steps (status as of 2025-05-07)**

1. ✅ Convert each milestone 3.x service into a proper Python package and ensure smoke tests import every `main.app` entry point.
2. ✅ Define the shared Postgres service in `docker-compose.yml` and remove the orphaned `finetune` container entry.
3. ✅ Script the end-to-end pipeline (ASR ➝ validation ➝ chunking ➝ index rebuild) so it can be triggered deterministically and captured in CI via `scripts/run_pipeline.py`.
4. ⏳ Backfill the monitoring plan once services actually emit metrics; Prometheus wiring is documented but remains in a planned state until real signals exist.

This audit section supersedes the optimistic milestone notes further below until the fixes above land.

---

## 1. Project Structure

### 📁 Folder Layout

```
CIRS/
├── backend/
│   ├── ingestion/
│   │   ├── instagram/          # Playwright + yt-dlp downloader, metadata storage
│   │   ├── youtube/            # yt-dlp ingestion with JSON sidecar export
│   │   ├── epub/               # EPUB parser using epub2txt / Unstructured.io
│   │   ├── pdf/                # PDF extraction using PyMuPDF or Unstructured.io
│   │   └── other_videos/       # Generic video ingestion (non-IG/YT)
│   ├── transcription/          # WhisperX GPU ASR + diarization pipeline
│   ├── processing/             # Chunking, tagging, embeddings, enrichment
│   ├── retrieval/              # Search and RAG orchestration services
│   ├── curriculum/             # Module builder (learning objectives, quizzes)
│   ├── api/                    # FastAPI backend, endpoint orchestration
│   └── utils/                  # Shared libraries (logging, hashing, file ops)
│
├── data/
│   ├── epub/                   # EPUB content, extracted text, metadata
│   ├── instagram/
│   │   ├── dataset/            # Final structured outputs for RAG
│   │   ├── db/                 # Local SQLite (ingestion state)
│   │   ├── downloads/          # Raw media files
│   │   └── transcripts/        # Transcribed text outputs
│   ├── youtube/
│   │   ├── downloads/          # Raw video files
│   │   └── transcripts/        # Generated transcripts
│   ├── pdf/                    # Extracted PDFs and metadata
│   ├── other_videos/
│   │   ├── downloads/
│   │   └── transcripts/
│   ├── db/                     # Core Postgres catalog and Qdrant vector store
│   ├── embeddings/             # Serialized embeddings (.npy / .json)
│   └── logs/                   # Structured pipeline logs
│
├── frontend/
│   ├── react_app/              # UI for querying, viewing modules & transcripts
│   ├── components/             # Chat UI, transcript viewer, module builder
│   └── assets/                 # Images, CSS, icons
│
├── .env                        # Environment variables (API keys, DB URLs)
├── .gitignore
├── Dockerfile
├── docker-compose.yml          # Service orchestration
├── Planning.md                 # This document
├── requirements.txt            # Python dependencies
└── README.md                   # Quick start + architecture summary
```

---

## 2. Core Components

### 2.1 Ingestion Layer

Responsible for acquiring data from various media platforms and formats.

* **Instagram / YouTube / Other Videos**: Uses Playwright or yt-dlp to scrape and download video content. Generates metadata JSON sidecars.
* **EPUB / PDF**: Extracts text using Unstructured.io or PyMuPDF; preserves headings, figures, and page data.
* **Operational DBs**: Each ingestion source has a small local SQLite DB for state tracking (cursors, seen IDs, rate limits).
* **Sync Service**: Periodically syncs metadata to the central Postgres Core Catalog.

### 2.2 Transcription Layer

* **WhisperX GPU Pipeline**: Performs ASR on video/audio sources using CUDA.
* **Diarization (optional)**: pyannote.audio for speaker segmentation.
* **Timestamp Alignment**: Ensures time-coded transcript output.
* **Storage**: Transcripts written to `/data/<source>/transcripts` and registered in Postgres.

### 2.3 Processing Layer

* **Text Cleaning**: Remove filler words, normalize casing.
* **Chunking**: Segment by semantic units or timecodes.
* **Entity Recognition**: Extract clinical terms and topic tags (spaCy/MedSpaCy).
* **Embeddings**: Generate using BGE or Instructor models on GPU.
* **Metadata Enrichment**: Adds provenance info, author, timestamps, license.

#### Pipeline Automation

* `scripts/run_pipeline.py` orchestrates the ASR ➝ validation ➝ chunking sequence with a single command so CI can rebuild indexes deterministically.
* Pass `--fresh` to clear resumability indexes (`.processed_index.json`, `.validated_index.json`, `.embedded_index.json`) before executing.
* Outputs a JSON summary to `data/pipeline_runs/<run_tag>.json` that records counts from each stage for auditability.

### 2.4 Database & Metadata Architecture

#### Hybrid Strategy

* **Core Catalog (Postgres)** — authoritative metadata and cross-source relationships.
* **Service-local DBs (SQLite)** — local ingestion state per source.
* **Vector Store (Qdrant)** — embeddings and payloads (chunk_id, source_id, timestamps/pages).
* **JSON Sidecars** — redundant raw metadata for resiliency.

#### Core Catalog Schema (Postgres)

Tables:

* `sources`: cross-platform metadata (type, URL, authors, SHA256, etc.)
* `transcripts`: full text + segments
* `documents`: text from PDF/EPUB
* `chunks`: retrievable text units with tags/entities
* `embeddings`: references to Qdrant vectors
* `jobs`: ingestion + processing logs (with idempotency)

Indexes:

* Unique: `sha256`, `idempotency_key`
* GIN: `topic_tags`, `entities`

### 2.5 Retrieval Layer

* **Hybrid Search**: Combines vector (semantic) + lexical (BM25) retrieval.
* **RAG Orchestrator**: Provides context to LLMs for grounded answers.
* **Citation Integrity**: Returns inline `[source_id@t=00:45-00:55]` style references.

### 2.6 Curriculum Builder

* **Input**: Retrieved text corpus or topic query.
* **Process**:

  1. Cluster by theme (semantic similarity)
  2. Extract key ideas & objectives (Bloom’s verbs)
  3. Build structured lesson JSON (sections, quizzes, references)
  4. Export to Markdown/HTML for frontend rendering.
* **Output**: Teachable module JSONs with citations + reading list.

### 2.7 Frontend (React)

* **Chat Interface**: Conversational retrieval with inline citations.
* **Transcript Viewer**: Linked timecodes; media playback.
* **Module Builder View**: Editable learning modules.
* **Admin Dashboard**: Monitor jobs, ingestion status, errors.

### 2.8 DevOps & Monitoring

* Docker Compose orchestration.
* Prometheus + Grafana for metrics.
* Loki or OpenTelemetry for logs.
* Sentry (optional) for error tracking.
* **Status**: Prometheus endpoints exist on milestone 3.x services but remain in "planned" mode until real metrics flow from the pipeline automation work above.

---

## 3. Data Flow Overview

1. Ingest → Metadata to SQLite → Sync to Postgres
2. ASR / Extraction → Cleaned text → Chunking → Embeddings → Qdrant
3. Retrieval → Query → Vector + Metadata join → RAG Answer
4. Curriculum Builder → Cluster → Summarize → Module JSON

---

## 4. Atomic Milestones

### Milestone 1 – Hybrid Database & Instagram Integration

* Setup Postgres Core Catalog.
* Maintain local SQLite for IG ingestion state.
* Sync successful downloads and metadata to Postgres.
* Store JSON sidecar paths.
* Verify deduplication (sha256, idempotency).

### Milestone 2 – Multi-Source Ingestion (YouTube, PDFs, EPUBs)

* Extend ingestion framework to multiple source types.
* Standardize ingestion metadata.
* Integrate Postgres upserts.

### Milestone 3 – Transcription & Text Extraction

* Implement WhisperX + diarization.
* Add PDF/EPUB extraction pipeline.
* Populate transcripts/documents tables.

### Milestone 4 – Chunking, Tagging & Embeddings

* Implement semantic chunking & tagging.
* Generate embeddings via GPU models.
* Index data in Qdrant; sync payloads to Postgres.

### Milestone 5 – RAG Chat Layer

* Develop hybrid retrieval (Qdrant + Postgres).
* Add context selection & LLM integration.
* Implement citation rendering.

### Milestone 6 – Curriculum Builder

* Build clustering & summarization pipeline.
* Generate structured modules with objectives/quizzes.

### Milestone 7 – Frontend UI

* Implement chat, transcript viewer, and module explorer.
* Add admin dashboard for ingestion/processing status.

### Milestone 8 – Monitoring & Ops

* Integrate Grafana dashboards, job logs, schema versioning.
* Automate backups & data integrity checks.

---

## 6. Medical Accuracy & Validation Strategy

### Goal

Ensure transcriptions and embeddings of medical content are accurate, consistent, and free of hallucinations through multi-layer verification, domain-specific models, and human validation.

### 6.1 Domain-Aware Transcription

* **Model Ensemble:** Use WhisperX (base) + Whisper-Large or specialized medical ASR models for redundancy.
* **Alignment Voting:** Keep words confirmed by ≥2 models.
* **Lexicon Integration:** Cross-check all tokens against UMLS, SNOMED-CT, RxNorm, and MeSH.
* **Fuzzy Term Matching:** Automatically correct common mishears using fuzzy string comparison (e.g., “hemotoma” → “hematoma”).

### 6.2 Post-Processing Validation

* **Medical Term Correction:** Run a correction pipeline post-ASR using Med7 or spaCy with biomedical vocab.
* **Context-Aware Verification:** Use BioGPT or ClinicalCamel to detect and flag illogical phrases.
* **Audit Logging:** Record all corrections as JSON `{original, corrected, method}` for traceability.

### 6.3 Confidence Scoring

Each transcript segment includes multiple confidence signals:

```json
{
  "segment_id": "uuid",
  "start_time": 32.4,
  "end_time": 48.2,
  "text": "The patient presented with tachycardia and hypotension",
  "asr_confidence": 0.94,
  "term_accuracy": 0.99,
  "final_confidence": 0.965,
  "version": "whisperX-v3.1+medlex-v1"
}
```

* Combine ASR + term accuracy + semantic coherence for an aggregate confidence.
* Version all transcripts under `/data/<source>/transcripts/versions/`.

### 6.4 Embedding Validation

* Use **BioBERT**, **ClinicalBERT**, or **PubMedBGE** for embeddings.
* Store `embedding_model` and `embedding_version` in DB.
* Maintain dual representation: semantic (BERT) + lexical (BM25/TF-IDF).
* Normalize all medical entities to canonical forms before embedding.

### 6.5 Human-in-the-Loop QA

* UI for human review:

  * Highlight segments <0.9 confidence.
  * Allow inline edits → stored as new transcript versions.
* “Verified by Human” flag in Postgres for gold-standard segments.

### 6.6 Workflow Orchestration

**Pipeline sequence:**

1. ASR job → initial transcript.
2. Lexicon correction job → fixed transcript.
3. Validation job → compute metrics + audit logs.
4. Embedding job → create domain embeddings.
5. Verification service → ensure entity grounding before indexing.

**Postgres tables:**

* `transcripts`: versioned entries.
* `term_corrections`: audit records.
* `quality_metrics`: confidence scores, error rates.

### 6.7 New Milestone

#### **Milestone 3.5 – Medical Accuracy Assurance**

**Goal:** Guarantee high-fidelity transcription and embedding of medical terminology.
**Tasks:**

* Integrate UMLS/SNOMED/RxNorm pipelines.
* Implement fuzzy term correction and confidence scoring.
* Apply MedLLM-based contextual validation.
* Add transcript versioning and quality metrics.
  **Definition of Done:** ≥98% verified term accuracy across test set; confidence logs stored in DB.

---

## 7. Knowledge Modeling & Curriculum Orchestration

### Goal

Transform unstructured, sporadic medical information into coherent, pedagogically structured learning content. Build a system that organizes extracted data into conceptual groupings, establishes relationships between them, and generates structured modules optimized for systematic learning.

### 7.1 Organizational Framework

**Three-tier structure:**

| Stage             | Description                                            | Output                                               |
| ----------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| **Collection**    | Raw transcripts, extracted text, metadata, embeddings. | Segmented `chunks` with provenance.                  |
| **Understanding** | Clustering, tagging, and semantic linking of concepts. | Structured *concept graphs*.                         |
| **Teaching**      | Curriculum generation and learning scaffolds.          | JSON “modules” with lessons, quizzes, and summaries. |

### 7.2 Semantic Clustering & Topic Modeling

* **Topic Discovery:** Use BERTopic, Top2Vec, or HDBSCAN + BGE embeddings to cluster related chunks.
* **Cluster Labeling:** Generate topic labels via context-bound LLM summarization (e.g., “Cytokine Cascade”, “Detoxification Pathways”).
* **Hierarchical Grouping:** Build multi-level hierarchies (micro-concepts → modules → domains).
* **Cross-Source Linking:** Match topics across platforms using canonical identifiers (UMLS/MeSH).

### 7.3 Curriculum Generation Workflow

1. **Learning Objectives Extraction:** Use LLMs tuned to Bloom’s taxonomy to derive measurable learning goals.
2. **Module Composition:** Build lessons from clustered chunks with summaries, citations, diagrams, and comprehension checks.
3. **Progressive Difficulty:** Organize content by complexity (introductory → advanced).
4. **Output Structure:** Export JSON modules with `objectives`, `sections`, `citations`, and `quizzes`.

**Example JSON:**

```json
{
  "module_id": "m_cirs_binders",
  "title": "Detoxification and Binding Agents in CIRS",
  "objectives": [
    "Describe the mechanism of bile acid sequestrants.",
    "Explain how cholestyramine aids toxin elimination."
  ],
  "sections": [
    {
      "title": "Overview of Binders",
      "summary": "Binders reduce circulating biotoxins by...",
      "citations": ["source_ig_0123@t=12:30-13:10", "paper_2024_cirs.pdf@p=4"]
    }
  ],
  "quizzes": [
    {"q": "What is the primary action of cholestyramine?", "a": "Binds biotoxins in the gut.", "type": "mcq"}
  ]
}
```

### 7.4 Concept Graph Data Model

* **concepts:** `concept_id`, `label`, `description`, `cluster_id`, `parent_id`.
* **modules:** `module_id`, `title`, `objective`, `syllabus_json`, `difficulty_level`.
* **concept_links:** `from_concept`, `to_concept`, `relation_type (causes|treats|is_a|inhibits)`.
* **evaluations:** `module_id`, `question`, `answer`, `type`, `difficulty`.

### 7.5 Workflow Automation

1. Retrieve and cluster `chunks` by semantic similarity.
2. Label clusters via LLM-based summarization.
3. Create or update related entries in `concepts` and `concept_links`.
4. Build structured modules with learning objectives, summaries, and quizzes.
5. Validate consistency across sources and store finalized modules in Postgres.

### 7.6 Model Recommendations

| Task                  | Recommended Models           | Purpose                       |
| --------------------- | ---------------------------- | ----------------------------- |
| Clustering            | BERTopic, HDBSCAN + BGE      | Identify conceptual groupings |
| Summarization         | GPT-4o, Gemini 2.5-Pro       | Generate topic labels         |
| Entity Linking        | SciSpacy, Med7, UMLS Matcher | Map to medical entities       |
| Curriculum Generation | Bloom-tuned LLMs             | Educational scaffolding       |
| Graph Structuring     | NetworkX + Postgres JSONB    | Concept relationships         |

### 7.7 Pedagogical Coherence Controls

* **Granularity Control:** Merge clusters smaller than N=5 chunks.
* **Citation Density:** Enforce ≥2 sources per concept.
* **Overlap Detection:** Compare summaries for duplication.
* **Curriculum Versioning:** Maintain `module_version` table for revision history.

### 7.8 New Milestone

#### **Milestone 6.5 – Knowledge Modeling & Curriculum Orchestration**

**Goal:** Organize clustered chunks into structured educational modules.
**Tasks:**

* Implement topic clustering and labeling pipeline.
* Generate concept graph and cross-source links.
* Auto-build learning modules with objectives, sections, and quizzes.
  **Definition of Done:** Structured modules are stored in DB with complete provenance, validated term accuracy, and coherent concept hierarchies.

---

## 8. Knowledge Graph Diagram

```mermaid
graph TD
  A[Chunks (transcribed + enriched text)] --> B[Concepts (semantic clusters)]
  B --> C[Modules (learning units)]
  C --> D[Curriculum (structured learning program)]
  B --> E[Concept Links (causal, hierarchical, associative)]
  A -->|Provenance| F[Sources (IG/YT/PDF/EPUB)]
  D --> G[Frontend (Learning UI)]
  F -->|Metadata sync| H[(Core Catalog - Postgres)]
  A -->|Vectors| I[(Qdrant Vector Store)]
```

### Diagram Explanation

* **Chunks → Concepts:** Semantically grouped segments of text become conceptual nodes.
* **Concepts → Modules:** Related concepts form modules with objectives and quizzes.
* **Modules → Curriculum:** Modules are ordered pedagogically into complete courses.
* **Concept Links:** Define relationships like *causes*, *treats*, *is_a*, or *inhibits*.
* **Sources:** Maintain traceability and citations to original media and documents.
* **Databases:** Postgres serves as the metadata core, while Qdrant manages semantic embeddings.

---

## 9. System Architecture & Runtime Orchestration Diagram

```mermaid
graph TD
  subgraph Ingestion Layer
    A1[Instagram Worker] --> A6
    A2[YouTube Worker] --> A6
    A3[EPUB Extractor] --> A6
    A4[PDF Extractor] --> A6
    A5[Other Video Worker] --> A6
    A6[Ingestion Controller]
  end

  subgraph Processing Layer
    B1[ASR GPU (WhisperX)] --> B2
    B2[Medical Validation Service] --> B3
    B3[Chunker + Tagger] --> B4
    B4[Embedder GPU]
  end

  subgraph Databases
    C1[(Postgres Core Catalog)]
    C2[(Qdrant Vector Store)]
    C3[(Local SQLite DBs)]
  end

  subgraph RAG & Curriculum
    D1[Retriever Service] --> D2
    D2[Chat Orchestrator] --> D3
    D3[Curriculum Builder]
  end

  subgraph Frontend & API
    E1[FastAPI Backend] --> E2
    E2[React Frontend]
  end

  A6 --> B1
  B4 --> C2
  B4 --> C1
  B3 --> C1
  C1 --> D1
  C2 --> D1
  D1 --> D2
  D2 --> E1
  D3 --> E1
  E1 --> E2
  C3 -.-> A6
  A6 --> C1
```

### Diagram Explanation

* **Ingestion Layer:** Each service ingests and preprocesses source content. Results and metadata are saved locally and synced to Postgres.
* **Processing Layer:** ASR, medical validation, chunking, tagging, and embedding all occur with GPU acceleration.
* **Databases:** Postgres stores authoritative metadata, Qdrant stores embeddings, and SQLite DBs maintain local ingestion states.
* **RAG & Curriculum:** Handles retrieval, grounded reasoning, and auto-generation of structured educational modules.
* **Frontend & API:** FastAPI provides endpoints for ingestion, retrieval, and curriculum management; React serves as the interactive UI.

---

## 10. Data Lifecycle Overview

```mermaid
graph LR
  A[Raw Sources (IG/YT/PDF/EPUB)] --> B[Ingestion Workers]
  B --> C[Local SQLite + JSON Sidecars]
  C --> D[Postgres Core Catalog]
  D --> E[ASR + Text Extraction]
  E --> F[Medical Validation Pipeline]
  F --> G[Chunking & Metadata Enrichment]
  G --> H[Embedding Generation (GPU)]
  H --> I[(Qdrant Vector Store)]
  I --> J[Retrieval & RAG]
  J --> K[Curriculum Builder]
  K --> L[Modules + Curriculum Exports]
  L --> M[Frontend Learning Interface]
```

### Lifecycle Explanation

1. **Ingestion:** Each worker downloads, parses, and stores content metadata with redundancy (SQLite + JSON sidecars).
2. **Synchronization:** Metadata syncs into Postgres, creating canonical `source_id` records.
3. **Extraction:** Audio → ASR; text → extraction. Each transcript versioned and validated.
4. **Validation:** Medical lexicon matching and context correction ensure factual precision.
5. **Chunking:** Text segmented into retrievable units with tags, timestamps, and provenance.
6. **Embedding:** GPU-generated domain embeddings stored in Qdrant with payloads referencing Postgres.
7. **Retrieval:** Vector + metadata hybrid search supports RAG queries and contextual answers.
8. **Curriculum:** Clusters of chunks form learning modules with objectives and quizzes.
9. **Frontend:** Exports appear as structured modules and visual learning flows in the UI.

---

## 11. Versioning & Reprocessing Strategy

### 11.1 Purpose

Ensure data consistency, reproducibility, and continuous improvement as models, extractors, and embeddings evolve. The system must track every processing version so that transcripts, embeddings, and modules can be regenerated safely and compared over time.

### 11.2 Versioning Principles

* **Immutable Inputs:** Raw downloads (audio, PDFs, EPUBs) never overwritten; stored by `sha256` hash.
* **Versioned Outputs:** Each stage of processing (ASR, validation, embedding, curriculum) produces new records tagged with version identifiers.
* **Reprocessing Safety:** Downstream stages use version references to determine if updates are required.

### 11.3 Version Tagging Schema

| Component             | Version Field                           | Example         | Stored In               |
| --------------------- | --------------------------------------- | --------------- | ----------------------- |
| ASR / Transcription   | `asr_model_version`                     | `whisperx-v3.1` | `transcripts` table     |
| Medical Validation    | `validation_version`                    | `medlex-v1.0`   | `quality_metrics` table |
| Embeddings            | `embedding_model` + `embedding_version` | `pubmedbge-v2`  | `embeddings` table      |
| Curriculum Generation | `curriculum_version`                    | `cbuilder-v1.2` | `modules` table         |

### 11.4 Reprocessing Triggers

* **Model Update:** New model version detected → automatic requeue for dependent tasks.
* **Data Drift:** New content appended to a source triggers downstream refresh for affected modules.
* **Manual Override:** Admin triggers full or partial reprocessing via CLI or UI.

### 11.5 Reprocessing Workflow

1. **Detection:** Compare current version against latest in registry.
2. **Dependency Map:** Identify affected tables (e.g., new ASR → refresh chunks + embeddings).
3. **Reprocessing Job:** Run updated pipelines only on stale records.
4. **Version Bump:** Update version fields and log in `jobs`.
5. **Audit Trail:** Maintain full record of old vs. new outputs for regression validation.

### 11.6 Rollback & Comparison

* Maintain snapshot of prior outputs in `/data/versions/` with timestamped folders.
* Include diff utilities (text + embedding similarity) for before/after analysis.
* Allow rollback to previous version in the UI for quality control.

### 11.7 Metadata Tables to Support Versioning

* `model_registry`: Tracks available ASR/embedding/validation versions.
* `reprocessing_jobs`: Logs affected sources, duration, and new outputs.
* `version_history`: Maintains provenance for each content stage.

---

## 12. Quality Assurance & Evaluation Metrics

### 12.1 Objectives

Establish measurable quality bars for every stage—ingestion, transcription, validation, retrieval, RAG answers, and curriculum—so we can detect regressions and maintain medical-grade accuracy.

### 12.2 Test Data & Golden Sets

* **Seed Sets:** Curate 50–100 representative videos (IG/YT) and 50+ PDFs/EPUBs spanning key topics.
* **Gold Transcripts:** Human-verified transcripts for a subset (≥10 hrs audio) with timecodes.
* **Gold Concepts:** Human-labeled concept clusters for 10 topics with canonical UMLS/MeSH tags.
* **Gold Q&A:** 200–300 questions with gold answers + citations from the source materials.
* **Split:** Train/dev/test splits to evaluate changes over time.

### 12.3 Ingestion & Parsing

* **File Integrity:** SHA256 match rate = 100%.
* **Sidecar Completeness:** ≥ 99% of ingests have a valid JSON sidecar recorded in Postgres.
* **Parser Coverage:** PDFs/EPUBs with structure JSON ≥ 98%.

### 12.4 ASR & Text Extraction

* **Word Error Rate (WER):** ≤ 12% on medical gold audio; report by source/language.
* **Character Error Rate (CER):** ≤ 6% on difficult segments (heavy jargon).
* **Medical Term Accuracy:** ≥ 98% exact/normalized match against UMLS/SNOMED target lists.
* **Timestamp Drift:** Median |ASR time – gold time| ≤ 300 ms per segment.

### 12.5 Medical Validation & Entity Linking

* **Entity Precision / Recall (macro):** ≥ 0.95 / ≥ 0.92 for key entity types (diseases, drugs, pathways).
* **Canonicalization Rate:** ≥ 98% mapped to UMLS/MeSH canonical forms.
* **Correction Audit:** 100% of term corrections logged with `{original, corrected, method}`.

### 12.6 Chunking & Embeddings

* **Chunk Cohesion (Human Rated 1–5):** ≥ 4.2 median.
* **Boundary Accuracy:** ≥ 95% of chunk boundaries align with semantic/timestamp edges.
* **Embedding Drift Check:** Cosine similarity to previous version ≥ 0.92 for unchanged texts.
* **Model Traceability:** 100% of vectors store `embedding_model` + `embedding_version`.

### 12.7 Retrieval & Ranking

* **Precision@k:** P@5 ≥ 0.75 on gold Q&A; P@10 ≥ 0.85.
* **nDCG@k:** nDCG@10 ≥ 0.85.
* **Recall@k:** R@50 ≥ 0.95 for recall-sensitive tasks.
* **Latency (p95):** ≤ 600 ms for retrieve-only; ≤ 1.5 s retrieve+rerank on local GPU.

### 12.8 RAG Answer Quality

* **Citation Density:** ≥ 2 unique citations per answer (median) unless trivial.
* **Grounding Score:** ≥ 0.9 (fraction of answer sentences supported by retrieved spans).
* **Hallucination Rate:** ≤ 1% (answers containing unsupported claims).
* **Faithfulness (Human Rated 1–5):** ≥ 4.4 median; disagreements adjudicated.

### 12.9 Curriculum & Pedagogy

* **Objective Quality (Bloom’s):** ≥ 90% objectives use measurable verbs.
* **Coverage Score:** ≥ 0.9 (fraction of required subtopics included per module spec).
* **Question Validity:** ≥ 95% items have unambiguous keys and correct rationales.
* **Readability (FKGL):** Target FKGL 10–12 for clinician-level; adjustable per audience.

### 12.10 Monitoring & Dashboards

* **Grafana Panels:** WER/CER, entity P/R, retrieval P@k/nDCG, latency, GPU util, job failures.
* **Quality Gates in CI:** Block merges if metrics regress > X% versus baseline.
* **Drift Alerts:** Trigger reprocessing when models or distributions change.

### 12.11 Human-in-the-Loop

* **Review UI:** Surface low-confidence segments (<0.9), allow quick corrections.
* **Spot Audits:** 5% random sample of new content weekly for manual checks.
* **Adjudication Workflow:** Resolve disagreements; update gold sets.

### 12.12 Milestone

#### **Milestone 8.5 – Quality & Evaluation Framework**

**Goal:** Implement metrics, gold sets, dashboards, and CI quality gates across the pipeline.
**Tasks:**

* Build gold datasets and loaders.
* Implement evaluators for WER/CER, entity P/R, retrieval metrics, and RAG faithfulness.
* Create Grafana dashboards & CI gates.
  **Definition of Done:** Quality dashboards live; PRs blocked on regression; weekly quality report generated.

---

## 13. Core Catalog – Postgres DDL

> Drop-in DDL to initialize the **authoritative Core Catalog**. Use with docker’s init folder or via `psql`.

```sql
-- 00_core_catalog.sql
CREATE SCHEMA IF NOT EXISTS cirs;
SET search_path TO cirs, public;

-- === ENUMS ===
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type') THEN
    CREATE TYPE source_type AS ENUM ('instagram','youtube','pdf','epub','other_video','other');
  END IF;
END $$;

-- === TABLES ===
CREATE TABLE IF NOT EXISTS sources (
  source_id UUID PRIMARY KEY,
  source_type source_type NOT NULL,
  original_url TEXT,
  platform_id TEXT, -- e.g., IG shortcode, YT id, DOI, etc.
  title TEXT,
  authors TEXT[],
  publish_date DATE,
  license TEXT,
  duration_sec INTEGER,
  language TEXT,
  local_path TEXT NOT NULL,
  sha256 TEXT NOT NULL UNIQUE,
  ingest_date TIMESTAMPTZ NOT NULL DEFAULT now(),
  extractor_version TEXT,
  raw_sidecar_path TEXT
);

CREATE TABLE IF NOT EXISTS transcripts (
  transcript_id UUID PRIMARY KEY,
  source_id UUID NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
  full_text TEXT NOT NULL,
  segments_json JSONB NOT NULL,
  quality_metrics JSONB,
  asr_model_version TEXT,
  validation_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  doc_id UUID PRIMARY KEY,
  source_id UUID NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  structure_json JSONB,
  extractor_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  chunk_id UUID PRIMARY KEY,
  parent_type TEXT CHECK (parent_type IN ('transcript','document')),
  parent_id UUID NOT NULL,
  source_id UUID NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  start_time DOUBLE PRECISION, -- seconds for transcripts
  end_time DOUBLE PRECISION,
  page INTEGER,                -- for PDFs/EPUBs
  section_path TEXT,
  topic_tags TEXT[],
  entities JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- for FK-like integrity across polymorphic parent_type
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_chunks_tags ON chunks USING GIN (topic_tags);
CREATE INDEX IF NOT EXISTS idx_chunks_entities ON chunks USING GIN (entities);

CREATE TABLE IF NOT EXISTS embeddings (
  chunk_id UUID PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  -- vector lives in Qdrant; this table tracks lineage
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id UUID PRIMARY KEY,
  job_type TEXT NOT NULL,
  source_id UUID REFERENCES sources(source_id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  idempotency_key TEXT UNIQUE,
  logs_path TEXT
);

-- Knowledge modeling tables
CREATE TABLE IF NOT EXISTS concepts (
  concept_id UUID PRIMARY KEY,
  label TEXT NOT NULL,
  description TEXT,
  cluster_id TEXT,
  parent_id UUID REFERENCES concepts(concept_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS concept_links (
  from_concept UUID REFERENCES concepts(concept_id) ON DELETE CASCADE,
  to_concept   UUID REFERENCES concepts(concept_id) ON DELETE CASCADE,
  relation_type TEXT NOT NULL, -- causes|treats|is_a|inhibits
  PRIMARY KEY (from_concept, to_concept, relation_type)
);

CREATE TABLE IF NOT EXISTS modules (
  module_id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  objective TEXT,
  syllabus_json JSONB NOT NULL,
  difficulty_level TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evaluations (
  eval_id UUID PRIMARY KEY,
  module_id UUID NOT NULL REFERENCES modules(module_id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  qtype TEXT NOT NULL, -- mcq|short|cloze
  difficulty TEXT
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_sources_publish_date ON sources(publish_date);
CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source_id);
```

---

## 14. Python ORM & Upsert Helpers (SQLAlchemy 2.0)

> Minimal models + idempotent upserts for `sources`, `transcripts`, and `chunks`. Adjust paths to the project layout.

```python
# backend/api/db/models.py
from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import (
    Enum, ForeignKey, JSON, UniqueConstraint, Index,
    text, func
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import create_engine
import enum

class Base(DeclarativeBase):
    pass

class SourceType(enum.Enum):
    instagram = 'instagram'
    youtube = 'youtube'
    pdf = 'pdf'
    epub = 'epub'
    other_video = 'other_video'
    other = 'other'

class Source(Base):
    __tablename__ = 'sources'
    __table_args__ = {"schema": "cirs"}

    source_id: Mapped[str] = mapped_column(primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type", create_constraint=False), nullable=False)
    original_url: Mapped[Optional[str]]
    platform_id: Mapped[Optional[str]]
    title: Mapped[Optional[str]]
    authors: Mapped[Optional[list[str]]] = mapped_column(ARRAY(text("text")))
    publish_date: Mapped[Optional[datetime]]
    license: Mapped[Optional[str]]
    duration_sec: Mapped[Optional[int]]
    language: Mapped[Optional[str]]
    local_path: Mapped[str]
    sha256: Mapped[str]
    ingest_date: Mapped[datetime] = mapped_column(server_default=func.now())
    extractor_version: Mapped[Optional[str]]
    raw_sidecar_path: Mapped[Optional[str]]

Index("idx_sources_publish_date", Source.publish_date, schema="cirs")
Index("idx_sources_type", Source.source_type, schema="cirs")

class Transcript(Base):
    __tablename__ = 'transcripts'
    __table_args__ = {"schema": "cirs"}

    transcript_id: Mapped[str] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("cirs.sources.source_id", ondelete="CASCADE"), nullable=False)
    full_text: Mapped[str]
    segments_json: Mapped[dict] = mapped_column(JSON)
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    asr_model_version: Mapped[Optional[str]]
    validation_version: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class Chunk(Base):
    __tablename__ = 'chunks'
    __table_args__ = {"schema": "cirs"}

    chunk_id: Mapped[str] = mapped_column(primary_key=True)
    parent_type: Mapped[str]
    parent_id: Mapped[str]
    source_id: Mapped[str] = mapped_column(ForeignKey("cirs.sources.source_id", ondelete="CASCADE"), nullable=False)
    text: Mapped[str]
    start_time: Mapped[Optional[float]]
    end_time: Mapped[Optional[float]]
    page: Mapped[Optional[int]]
    section_path: Mapped[Optional[str]]
    topic_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(text("text")))
    entities: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

```python
# backend/api/db/upserts.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def upsert_source(session: AsyncSession, payload: dict) -> str:
    sql = text(
        """
        INSERT INTO cirs.sources (
          source_id, source_type, original_url, platform_id, title, authors, publish_date,
          license, duration_sec, language, local_path, sha256, extractor_version, raw_sidecar_path
        ) VALUES (
          :source_id, :source_type, :original_url, :platform_id, :title, :authors, :publish_date,
          :license, :duration_sec, :language, :local_path, :sha256, :extractor_version, :raw_sidecar_path
        )
        ON CONFLICT (sha256) DO UPDATE SET
          title = COALESCE(EXCLUDED.title, cirs.sources.title),
          authors = COALESCE(EXCLUDED.authors, cirs.sources.authors),
          publish_date = COALESCE(EXCLUDED.publish_date, cirs.sources.publish_date),
          extractor_version = EXCLUDED.extractor_version,
          raw_sidecar_path = COALESCE(EXCLUDED.raw_sidecar_path, cirs.sources.raw_sidecar_path)
        RETURNING source_id;
        """
    )
    row = await session.execute(sql, payload)
    return row.scalar_one()

async def upsert_transcript(session: AsyncSession, payload: dict) -> str:
    sql = text(
        """
        INSERT INTO cirs.transcripts (
          transcript_id, source_id, full_text, segments_json, quality_metrics,
          asr_model_version, validation_version
        ) VALUES (
          :transcript_id, :source_id, :full_text, :segments_json, :quality_metrics,
          :asr_model_version, :validation_version
        )
        ON CONFLICT (transcript_id) DO UPDATE SET
          full_text = EXCLUDED.full_text,
          segments_json = EXCLUDED.segments_json,
          quality_metrics = EXCLUDED.quality_metrics,
          asr_model_version = EXCLUDED.asr_model_version,
          validation_version = EXCLUDED.validation_version
        RETURNING transcript_id;
        """
    )
    row = await session.execute(sql, payload)
    return row.scalar_one()

async def upsert_chunk(session: AsyncSession, payload: dict) -> str:
    sql = text(
        """
        INSERT INTO cirs.chunks (
          chunk_id, parent_type, parent_id, source_id, text, start_time, end_time, page, section_path, topic_tags, entities
        ) VALUES (
          :chunk_id, :parent_type, :parent_id, :source_id, :text, :start_time, :end_time, :page, :section_path, :topic_tags, :entities
        )
        ON CONFLICT (chunk_id) DO UPDATE SET
          text = EXCLUDED.text,
          start_time = EXCLUDED.start_time,
          end_time = EXCLUDED.end_time,
          page = EXCLUDED.page,
          section_path = EXCLUDED.section_path,
          topic_tags = EXCLUDED.topic_tags,
          entities = EXCLUDED.entities
        RETURNING chunk_id;
        """
    )
    row = await session.execute(sql, payload)
    return row.scalar_one()
```

```python
# backend/api/main.py (skeleton)
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class SourceIn(BaseModel):
    source_id: str
    source_type: str
    original_url: str | None = None
    platform_id: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    publish_date: str | None = None
    license: str | None = None
    duration_sec: int | None = None
    language: str | None = None
    local_path: str
    sha256: str
    extractor_version: str | None = None
    raw_sidecar_path: str | None = None

@app.get("/health")
async def health():
    return {"ok": True}
```

---

## 15. docker-compose.yml (Starter Stack)

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16
    container_name: cirs-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
    volumes:
      - ./data/db:/var/lib/postgresql/data
      - ./backend/db_init:/docker-entrypoint-initdb.d:ro

  qdrant:
    image: qdrant/qdrant:latest
    container_name: cirs-qdrant
    ports: ["6333:6333"]
    volumes:
      - ./data/qdrant:/qdrant/storage

  api:
    build: ./backend/api
    container_name: cirs-api
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      QDRANT_URL: http://qdrant:6333
    depends_on:
      - postgres
      - qdrant
    ports: ["8000:8000"]
    volumes:
      - ./backend/api:/app
      - ./data:/data

  # Optional: embedder/asr services added later

networks:
  default:
    name: cirs-net
```

> Place the SQL file in `backend/db_init/00_core_catalog.sql` so Postgres auto-initializes the schema.

---

## 16. Makefile (Convenience Targets)

```makefile
SHELL := /bin/bash

include .env

up:
	docker compose up -d --build

up-nc:
	docker compose up --build

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=200

stop:
	docker compose stop

Down:
	docker compose down -v

psql:
	@docker exec -it cirs-postgres psql -U $$POSTGRES_USER -d $$POSTGRES_DB

seed:
	@echo "(Optional) add seed scripts here"

api-dev:
	@docker exec -it cirs-api uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 17. .env.example

```env
POSTGRES_USER=cirs
POSTGRES_PASSWORD=cirs
POSTGRES_DB=cirs
DATABASE_URL=postgresql://cirs:cirs@localhost:5432/cirs
QDRANT_URL=http://localhost:6333
PYTHONUNBUFFERED=1
```

---

## 18. Backend/API Dockerfile (minimal)

```dockerfile
# backend/api/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 19. requirements.txt (starter)

```txt
fastapi
uvicorn[standard]
SQLAlchemy>=2.0
asyncpg
psycopg[binary]
python-dotenv
pydantic
```

---

## 20. Repo Wiring – Where to Place Files

```
CIRS/
├── backend/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── db/
│   │       ├── models.py
│   │       └── upserts.py
│   ├── db_init/
│   │   └── 00_core_catalog.sql
│   └── ingestion/ ... (as defined earlier)
├── data/
│   ├── db/
│   ├── qdrant/
│   └── ...
├── docker-compose.yml
├── Makefile
├── .env.example
├── requirements.txt
└── Planning.md
```

---

## 21. Smoke Test

1. Copy `.env.example` → `.env` and adjust as needed.
2. `make up` (first run initializes Postgres with Core Catalog).
3. `curl http://localhost:8000/health` → `{ "ok": true }`.
4. Point the IG downloader’s exporter to `DATABASE_URL` and call the `upsert_source` helper using SQLAlchemy or direct SQL.

---

## 22. Instagram → Core Catalog Sync

### 22.1 Purpose

Integrate existing local `videos.sqlite` ingestion database with the Core Catalog Postgres schema. This allows seamless transition from isolated Instagram ingestion to unified metadata tracking across all platforms.

### 22.2 Current Local Schema

```sql
CREATE TABLE video (
  id VARCHAR NOT NULL,
  filename VARCHAR NOT NULL,
  downloaded_at DATETIME NOT NULL,
  json_metadata VARCHAR NOT NULL,
  PRIMARY KEY (id)
);
```

### 22.3 Field Mapping

| Local Field     | Description                             | Core Catalog Field           |
| --------------- | --------------------------------------- | ---------------------------- |
| `id`            | Instagram reel shortcode or internal ID | `platform_id`                |
| `filename`      | Local video filename or path            | `local_path`                 |
| `downloaded_at` | Download timestamp                      | `ingest_date`                |
| `json_metadata` | Raw scraper metadata JSON               | Expanded fields in `sources` |

### 22.4 Sync Architecture

* **Keep SQLite:** Acts as local ingestion tracker (deduplication, retry safety).
* **Postgres Core Catalog:** Central cross-source metadata registry.
* **Sync Script:** Reads from SQLite → parses `json_metadata` → upserts into Postgres via `upsert_source()`.

### 22.5 Example Sync Script

```python
import sqlite3, json, uuid, asyncio
from db.upserts import upsert_source
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine("postgresql+asyncpg://cirs:cirs@localhost:5432/cirs")

async def sync_instagram_to_core():
    conn = sqlite3.connect("videos.sqlite")
    cur = conn.cursor()
    cur.execute("SELECT id, filename, downloaded_at, json_metadata FROM video")
    rows = cur.fetchall()

    async with AsyncSession(engine) as session:
        for id_, filename, downloaded_at, meta_str in rows:
            meta = json.loads(meta_str)
            payload = {
                "source_id": str(uuid.uuid4()),
                "source_type": "instagram",
                "original_url": meta.get("url"),
                "platform_id": id_,
                "title": meta.get("title"),
                "authors": [meta.get("author")],
                "publish_date": meta.get("upload_date"),
                "license": meta.get("license"),
                "duration_sec": meta.get("duration"),
                "language": meta.get("language", "en"),
                "local_path": f"/data/instagram/downloads/{filename}",
                "sha256": meta.get("sha256", id_),
                "extractor_version": "ig_ingest_v1",
                "raw_sidecar_path": f"/data/instagram/dataset/{id_}.json",
            }
            await upsert_source(session, payload)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(sync_instagram_to_core())
```

### 22.6 Integration Flow

1. Instagram scraper updates `videos.sqlite` after each download.
2. Sync job runs periodically (manual or cron) to push new rows to Postgres.
3. Postgres Core Catalog now contains unified metadata for ingestion, transcription, and RAG.

### 22.7 Milestone

#### **Milestone 1.5 – Instagram → Core Catalog Sync**

**Goal:** Bridge local ingestion tracking and centralized metadata registry.
**Tasks:**

* Maintain local SQLite for ingestion reliability.
* Implement periodic sync to Postgres using async upserts.
* Verify deduplication via `sha256` and `platform_id`.
  **Definition of Done:** All downloaded videos appear in the `sources` table with accurate metadata and provenance.

---
## 23. Unified Transcription Pipeline (Audio & Video)

### 23.1 Overview

Audio and video sources share a unified transcription pipeline. The only difference is that videos require an audio extraction step before ASR processing. Both ultimately produce time-aligned, validated medical transcripts.

```mermaid
graph LR
A[Raw Audio or Video File] --> B[Audio Extraction (ffmpeg)]
B --> C[ASR GPU Service (WhisperX/Faster-Whisper)]
C --> D[Segmentation + Word-level Timestamps]
D --> E[Medical Validation Pipeline]
E --> F[Transcript Storage + Versioning]
F --> G[Chunker + Embeddings]
```

---

### 23.2 Audio Extraction

* **Video:** Extract audio with ffmpeg

  ```bash
  ffmpeg -i input.mp4 -ac 1 -ar 16000 output.wav
  ```
* **Audio:** No extraction needed.

---

### 23.3 ASR (Automatic Speech Recognition)

* Uses **WhisperX GPU container** for speed and accuracy.
* Produces `segments.json`, `transcript.txt`, and optional `confidence.json`.
* Outputs include:

  * Word-level timestamps
  * Model version tagging (`asr_model_version`)
  * Full text transcript

---

### 23.4 Medical Validation

* Pass transcripts through **UMLS/SNOMED/RxNorm** lexicon correction.
* Apply **contextual validation** using MedLLMs (BioGPT, ClinicalCamel).
* Assign confidence metrics per segment.

---

### 23.5 Transcript Storage

All transcripts (audio and video) share the same schema in Postgres `transcripts` table.

| Column               | Example         | Notes                 |
| -------------------- | --------------- | --------------------- |
| `transcript_id`      | UUID            | unique per ASR run    |
| `source_id`          | UUID            | links to `sources`    |
| `full_text`          | Cleaned text    | full transcript       |
| `segments_json`      | word timestamps | WhisperX output       |
| `quality_metrics`    | JSON            | WER, confidence, etc. |
| `asr_model_version`  | whisperx-v3.1   | model tag             |
| `validation_version` | medlex-v1.0     | validation tag        |

**Versioned output folders:**

```
/data/transcripts/audio/versions/
/data/transcripts/videos/versions/
```

---

### 23.6 Chunking & Embedding

After transcription and validation:

* Split text into 200–500 token semantic chunks.
* Generate embeddings using **BioBERT** or **PubMedBGE**.
* Store in Qdrant with provenance payloads:

  ```json
  {
    "source_id": "...",
    "start_time": 32.4,
    "end_time": 45.2,
    "parent_type": "transcript",
    "title": "CIRS Lecture 3",
    "authors": ["Dr. Dorninger"]
  }
  ```

---

### 23.7 Key Differences: Audio vs. Video

| Step                | Audio            | Video                     | Notes                      |
| ------------------- | ---------------- | ------------------------- | -------------------------- |
| Input Extraction    | Direct           | Extract with ffmpeg       | Required for ASR           |
| Timestamp Alignment | Audio time       | Audio + visual timecodes  | Enables deep-link playback |
| Metadata            | Simpler          | Includes frame/video info | Stored in `sources`        |
| OCR / Slides        | None             | Optional with `ocr_gpu`   | For visual text            |
| Post-processing     | Plain transcript | Add visual context        | For teachable modules      |

---

### 23.8 Storage & Versioning

Each run produces new versions:

* `v1`: Baseline ASR
* `v2`: After medical correction
* `v3`: Human-reviewed

Located at:

```
/data/transcripts/audio/versions/
/data/transcripts/videos/versions/
```

---

### 23.9 Summary Table

| Stage      | Audio               | Video               | Common Output           |
| ---------- | ------------------- | ------------------- | ----------------------- |
| Input      | .wav, .mp3          | .mp4, .mov          | Audio waveform          |
| Extraction | None                | ffmpeg              | .wav                    |
| ASR        | WhisperX            | WhisperX            | Transcript + timestamps |
| Validation | MedLex + BioLLM     | MedLex + BioLLM     | Cleaned transcript      |
| Chunking   | Semantic            | Semantic + visual   | chunks                  |
| Embeddings | BioBERT / PubMedBGE | BioBERT / PubMedBGE | vectors                 |
| Storage    | /transcripts/audio  | /transcripts/videos | DB + Qdrant             |

---

### 23.10 Milestone 2.5 – Unified Transcription & Validation

**Goal:** Establish unified transcription for audio/video with medical validation and versioning.
**Tasks:**

* Integrate ffmpeg extraction for video.
* Implement WhisperX ASR GPU service.
* Add lexicon validation and contextual correction.
* Store and version transcripts by media type.
  **Definition of Done:** Audio and video files produce validated transcripts with version control and recorded mo

## 24. Next Steps

* Add Alembic migrations once schemas stabilize.
* Introduce `/ingest/source` and `/search` endpoints.
* Wire Qdrant collections with a standard collection name (e.g., `cirs_chunks_v1`).
* Add GitHub Actions CI to run lint + unit tests + quality gates.

1. Scaffold repository with folder structure above.
2. Create Postgres schema + SQLAlchemy models.
3. Connect existing Instagram ingestion to Postgres sync.
4. Build modular ingestion interface for YouTube/PDF/EPUB.
5. Begin ASR pipeline with WhisperX GPU.
6. Establish Qdrant + embedding service.
7. Build basic FastAPI retrieval endpoint.
8. Integrate React frontend + chat sandbox.
