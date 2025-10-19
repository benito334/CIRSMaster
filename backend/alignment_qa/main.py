from fastapi import FastAPI, Body, Path
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from prometheus_client import Gauge, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from .aligner import align_answer_to_chunks
from .summarizer import summarize_alignment

registry = CollectorRegistry()
metric_coverage = Gauge('alignment_coverage', 'Sentence-level alignment coverage', registry=registry)
metric_agreement = Gauge('alignment_agreement', 'Agreement score across aligned sentences', registry=registry)

app = FastAPI(title="CIRS Alignment QA", version="0.1.0")


class AlignIn(BaseModel):
    answer_id: str
    answer_text: str
    retrieved_chunks: List[Dict[str, Any]]


class AlignOut(BaseModel):
    answer_id: str
    sentence_alignments: List[Dict[str, Any]]
    alignment_coverage: float
    agreement_score: float
    weak_claims: int
    summary: str
    timestamp: str


def maybe_write_db(payload: Dict[str, Any]) -> bool:
    import os
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cirs.answer_alignment (
              answer_id TEXT PRIMARY KEY,
              sentence_alignments JSONB NOT NULL,
              alignment_coverage DOUBLE PRECISION,
              agreement_score DOUBLE PRECISION,
              weak_claims INTEGER,
              created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            INSERT INTO cirs.answer_alignment (
              answer_id, sentence_alignments, alignment_coverage, agreement_score, weak_claims
            ) VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (answer_id) DO UPDATE SET
              sentence_alignments=EXCLUDED.sentence_alignments,
              alignment_coverage=EXCLUDED.alignment_coverage,
              agreement_score=EXCLUDED.agreement_score,
              weak_claims=EXCLUDED.weak_claims
            """,
            (
                payload['answer_id'],
                json.dumps(payload.get('sentence_alignments', [])),
                payload.get('alignment_coverage', 0.0),
                payload.get('agreement_score', 0.0),
                payload.get('weak_claims', 0),
            )
        )
        cur.close(); conn.close()
        return True
    except Exception:
        return False


@app.get('/health')
async def health():
    return {"ok": True}


@app.get('/metrics')
async def metrics():
    data = generate_latest(registry)
    return app.response_class(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post('/align', response_model=AlignOut)
async def align(body: AlignIn = Body(...)):
    result = align_answer_to_chunks(body.answer_text, body.retrieved_chunks)
    summary = summarize_alignment(result)
    metric_coverage.set(result.get('alignment_coverage', 0.0))
    metric_agreement.set(result.get('agreement_score', 0.0))
    out = {
        'answer_id': body.answer_id,
        'summary': summary,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **result,
    }
    maybe_write_db(out)
    return out


@app.get('/alignments/{answer_id}')
async def get_alignment(answer_id: str = Path(...)):
    import os
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"answer_id": answer_id, "found": False}
    try:
        import psycopg2, json as _json
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT sentence_alignments, alignment_coverage, agreement_score, weak_claims FROM cirs.answer_alignment WHERE answer_id=%s", (answer_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return {"answer_id": answer_id, "found": False}
        return {
            "answer_id": answer_id,
            "sentence_alignments": row[0],
            "alignment_coverage": row[1],
            "agreement_score": row[2],
            "weak_claims": row[3],
            "found": True,
        }
    except Exception:
        return {"answer_id": answer_id, "found": False}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8012)
