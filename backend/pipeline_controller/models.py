from dataclasses import dataclass
from typing import Optional
import psycopg2
import os

DB_URL = os.getenv("DB_URL")

DDL = """
CREATE SCHEMA IF NOT EXISTS cirs;
CREATE TABLE IF NOT EXISTS cirs.pipeline_status (
  file_id UUID PRIMARY KEY,
  source_id UUID NULL,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,
  asr_done BOOLEAN DEFAULT FALSE,
  validation_done BOOLEAN DEFAULT FALSE,
  embedding_done BOOLEAN DEFAULT FALSE,
  asr_error TEXT NULL,
  validation_error TEXT NULL,
  embedding_error TEXT NULL,
  last_update TIMESTAMP DEFAULT NOW(),
  run_tag TEXT NULL
);
"""

def init_db():
    if not DB_URL:
        return
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(DDL)
    cur.close()
    conn.close()
