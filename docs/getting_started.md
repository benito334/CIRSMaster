# Getting Started

- Prerequisites: Docker, Docker Compose, Python 3.11, NVIDIA Container Toolkit (for GPU services).
- Steps:
  - `git clone` the repo
  - `cp .env.example .env`
  - `make up`
  - Visit UI at http://localhost:5173 (if `ui_web` is enabled)
  - Test retrieval and chat via backend endpoints

## Quick Checks
- `docker compose ps` shows services up
- Postgres reachable via `DB_URL`
- Qdrant at http://localhost:6333
