from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import json

from prometheus_client import Gauge, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from .feedback_analyzer import aggregate_metrics
from .adaptive_trainer import compute_adjustments

registry = CollectorRegistry()
metric_avg_conf = Gauge('reinforce_avg_confidence', 'Average confidence', registry=registry)
metric_avg_agree = Gauge('reinforce_avg_agreement', 'Average agreement', registry=registry)
metric_hall_rate = Gauge('reinforce_hallucination_rate', 'Hallucination rate', registry=registry)
metric_weak_rate = Gauge('reinforce_weak_claim_rate', 'Weak claim rate', registry=registry)

app = FastAPI(title="CIRS Reinforcement Service", version="0.1.0")


class ReinforceOut(BaseModel):
    run_tag: str
    averages: Dict[str, Any]
    adjustments: Dict[str, Any]
    timestamp: str


def write_tuning_history(run_tag: str, averages: Dict[str, Any], adjustments: Dict[str, Any]) -> bool:
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
            CREATE TABLE IF NOT EXISTS cirs.model_tuning_history (
              run_tag TEXT PRIMARY KEY,
              avg_confidence DOUBLE PRECISION,
              avg_agreement DOUBLE PRECISION,
              hallucination_rate DOUBLE PRECISION,
              weak_claim_rate DOUBLE PRECISION,
              retrieval_top_k INT,
              chunk_overlap INT,
              summary_temperature DOUBLE PRECISION,
              created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            INSERT INTO cirs.model_tuning_history (
              run_tag, avg_confidence, avg_agreement, hallucination_rate, weak_claim_rate,
              retrieval_top_k, chunk_overlap, summary_temperature
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (run_tag) DO UPDATE SET
              avg_confidence=EXCLUDED.avg_confidence,
              avg_agreement=EXCLUDED.avg_agreement,
              hallucination_rate=EXCLUDED.hallucination_rate,
              weak_claim_rate=EXCLUDED.weak_claim_rate,
              retrieval_top_k=EXCLUDED.retrieval_top_k,
              chunk_overlap=EXCLUDED.chunk_overlap,
              summary_temperature=EXCLUDED.summary_temperature
            """,
            (
                run_tag,
                averages.get('avg_confidence'),
                averages.get('avg_agreement'),
                averages.get('hallucination_rate'),
                averages.get('weak_claim_rate'),
                adjustments.get('retrieval_top_k'),
                adjustments.get('chunk_overlap'),
                adjustments.get('summary_temperature'),
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


@app.post('/reinforce', response_model=ReinforceOut)
async def reinforce():
    averages = aggregate_metrics()
    adjustments = compute_adjustments(averages)
    metric_avg_conf.set(averages.get('avg_confidence') or 0.0)
    metric_avg_agree.set(averages.get('avg_agreement') or 0.0)
    metric_hall_rate.set(averages.get('hallucination_rate') or 0.0)
    metric_weak_rate.set(averages.get('weak_claim_rate') or 0.0)

    run_tag = datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')
    write_tuning_history(run_tag, averages, adjustments)
    out = {
        'run_tag': run_tag,
        'averages': averages,
        'adjustments': adjustments,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    return out


@app.get('/status')
async def status():
    import os
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"last": None}
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT run_tag, avg_confidence, avg_agreement, hallucination_rate, weak_claim_rate, retrieval_top_k, chunk_overlap, summary_temperature, created_at FROM cirs.model_tuning_history ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return {"last": None}
        return {
            "last": {
                "run_tag": row[0],
                "avg_confidence": row[1],
                "avg_agreement": row[2],
                "hallucination_rate": row[3],
                "weak_claim_rate": row[4],
                "retrieval_top_k": row[5],
                "chunk_overlap": row[6],
                "summary_temperature": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
            }
        }
    except Exception:
        return {"last": None}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8013)
