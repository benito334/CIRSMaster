# CIRS Agent Documentation

Welcome to the CIRS Agent developer documentation.

- Overview of a local-first, GPU-accelerated RAG system for medical content.
- Milestones 3.0–3.9 implemented: UI, Monitoring, Evaluation, Alignment, Reinforcement, Security, Backup, Auth, CI/CD.

```mermaid
flowchart LR
  A[Ingestion] --> B[ASR GPU]
  B --> C[Validation GPU]
  C --> D[Chunking + Embeddings]
  D --> E[Qdrant Vector DB]
  D --> F[BM25 Index]
  E --> G[Hybrid Retriever]
  F --> G
  G --> H[Chat Orchestrator]
  H --> I[Curriculum Builder]
  H --> J[Evaluation & Alignment]
  I --> K[Feedback]
  J --> L[Reinforcement]
```
