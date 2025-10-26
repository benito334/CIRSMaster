from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from prometheus_client import Counter, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
import json, os
<<<<<<< HEAD
from redactor import redact_text
=======
from .redactor import redact_text
>>>>>>> origin/codex/review-repository-for-issues-and-updates

registry = CollectorRegistry()
pii_counter = Counter('pii_redactions_total', 'PII redaction events', ['type'], registry=registry)

app = FastAPI(title="CIRS Security Guardrails", version="0.1.0")

class RedactRequest(BaseModel):
    text: str
    file_path: Optional[str] = None


def ensure_tables():
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
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
            CREATE SCHEMA IF NOT EXISTS cirs;
            CREATE TABLE IF NOT EXISTS cirs.redaction_log (
              redaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              file_path TEXT,
              entity TEXT,
              entity_type TEXT,
              timestamp TIMESTAMPTZ DEFAULT NOW()
            );
            """
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


@app.post('/redact')
async def redact(req: RedactRequest = Body(...)):
    ensure_tables()
    redacted, ents = redact_text(req.text)
    DB_URL = os.getenv('DB_URL')
    if DB_URL and ents:
        try:
            import psycopg2
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()
            for e in ents:
                pii_counter.labels(type=e['label']).inc()
                cur.execute(
                    "INSERT INTO cirs.redaction_log (file_path, entity, entity_type) VALUES (%s, %s, %s)",
                    (req.file_path, e['text'], e['label'])
                )
            cur.close(); conn.close()
        except Exception:
            pass
    log_path = os.getenv('REDACTION_LOG_PATH', '/data/security/redaction_log.json')
    if ents:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            for e in ents:
                f.write(json.dumps({
                    'file': req.file_path,
                    'entity': e['text'],
                    'type': e['label']
                })+'\n')
    return {"text": redacted, "entities": ents}


@app.get('/audit')
async def audit(limit: int = Query(100)):
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"items": []}
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT file_path, entity, entity_type, timestamp FROM cirs.redaction_log ORDER BY timestamp DESC LIMIT %s", (limit,))
        rows = cur.fetchall(); cur.close(); conn.close()
        items = []
        for r in rows:
            items.append({"file_path": r[0], "entity": r[1], "entity_type": r[2], "timestamp": r[3].isoformat() if r[3] else None})
        return {"items": items}
    except Exception:
        return {"items": []}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8016)
