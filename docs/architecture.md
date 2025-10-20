# Architecture

High-level service map and data flow.

```mermaid
flowchart TD
  ingest[Ingestion] --> asr[ASR GPU]
  asr --> validate[Validation GPU]
  validate --> chunk[Chunking & Embeddings]
  chunk --> qdrant[Qdrant]
  chunk --> bm25[BM25 Index]
  qdrant --> retriever[Hybrid Retriever]
  bm25 --> retriever
  retriever --> chat[Chat Orchestrator]
  chat --> module[Curriculum Builder]
  chat --> eval[Evaluation]
  chat --> align[Alignment QA]
  eval --> reinforce[Reinforcement]
  align --> reinforce
  module --> feedback[Feedback]
  feedback --> reinforce
  security[Security Guardrails] -.-> validate
  license[License Audit] -.-> module
  backup[Backup] -.-> (Storage)
  auth[Auth & RBAC] --> chat
```
