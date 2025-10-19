from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from prometheus_client import Gauge, Histogram, CONTENT_TYPE_LATEST
from prometheus_client import CollectorRegistry, generate_latest

from .scorer import score_answer
from .validator import validate_medical_grounding

registry = CollectorRegistry()
metric_conf = Gauge('eval_confidence_answer', 'Answer confidence score', registry=registry)
metric_support = Gauge('eval_support_ratio', 'Support ratio', registry=registry)
metric_halluc = Gauge('eval_hallucination_risk', 'Hallucination risk', registry=registry)
metric_eval_latency = Histogram('eval_latency_ms', 'Evaluation latency (ms)', registry=registry)

app = FastAPI(title="CIRS Evaluation Service", version="0.1.0")


class EvalIn(BaseModel):
    answer_id: str
    answer_text: str
    citations: List[Dict[str, Any]] = []
    retrieved_chunks: List[Dict[str, Any]] = []


class EvalOut(BaseModel):
    answer_id: str
    confidence_answer: float
    support_ratio: float
    citation_density: float
    hallucination_risk: float
    missing_entities: List[str]
    validation_notes: str
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
        # Create table if not exists (lightweight idempotent)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cirs.answer_evaluations (
              answer_id TEXT PRIMARY KEY,
              confidence_answer DOUBLE PRECISION,
              support_ratio DOUBLE PRECISION,
              citation_density DOUBLE PRECISION,
              hallucination_risk DOUBLE PRECISION,
              missing_entities JSONB,
              validation_notes TEXT,
              payload_json JSONB,
              created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            INSERT INTO cirs.answer_evaluations (
              answer_id, confidence_answer, support_ratio, citation_density, hallucination_risk,
              missing_entities, validation_notes, payload_json
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (answer_id) DO UPDATE SET
              confidence_answer=EXCLUDED.confidence_answer,
              support_ratio=EXCLUDED.support_ratio,
              citation_density=EXCLUDED.citation_density,
              hallucination_risk=EXCLUDED.hallucination_risk,
              missing_entities=EXCLUDED.missing_entities,
              validation_notes=EXCLUDED.validation_notes,
              payload_json=EXCLUDED.payload_json
            """,
            (
                payload['answer_id'],
                payload['confidence_answer'],
                payload['support_ratio'],
                payload['citation_density'],
                payload['hallucination_risk'],
                json.dumps(payload.get('missing_entities', [])),
                payload.get('validation_notes', ''),
                json.dumps(payload),
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


@app.post('/evaluate', response_model=EvalOut)
async def evaluate(body: EvalIn = Body(...)):
    start = datetime.utcnow()
    scores = score_answer(body.answer_text, body.retrieved_chunks, body.citations)
    missing, note = validate_medical_grounding(body.answer_text, body.retrieved_chunks)
    ts = datetime.utcnow().isoformat() + 'Z'
    out = {
        'answer_id': body.answer_id,
        'timestamp': ts,
        **scores,
        'missing_entities': missing,
        'validation_notes': note,
    }
    # Update metrics
    metric_conf.set(out['confidence_answer'])
    metric_support.set(out['support_ratio'])
    metric_halluc.set(out['hallucination_risk'])
    elapsed_ms = (datetime.utcnow() - start).total_seconds() * 1000.0
    metric_eval_latency.observe(elapsed_ms)

    maybe_write_db(out)
    return out


@app.get('/history')
async def history(source_id: Optional[str] = Query(None)):
    # If DB available, return last 50 records
    import os
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"items": []}
    try:
        import psycopg2, json as _json
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        if source_id:
            cur.execute("SELECT answer_id, payload_json FROM cirs.answer_evaluations ORDER BY created_at DESC LIMIT 50")
        else:
            cur.execute("SELECT answer_id, payload_json FROM cirs.answer_evaluations ORDER BY created_at DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close(); conn.close()
        items = []
        for aid, payload in rows:
            if isinstance(payload, str):
                try:
                    payload = _json.loads(payload)
                except Exception:
                    payload = {"raw": payload}
            items.append({"answer_id": aid, **payload})
        return {"items": items}
    except Exception:
        return {"items": []}
