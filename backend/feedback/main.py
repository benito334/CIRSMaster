from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import Optional
from prometheus_client import Counter, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

<<<<<<< HEAD
from schema import AnswerFeedback, ModuleFeedback
=======
from .schema import AnswerFeedback, ModuleFeedback
>>>>>>> origin/codex/review-repository-for-issues-and-updates

registry = CollectorRegistry()
feedback_counter = Counter('feedback_total', 'User feedback count', ['type','rating'], registry=registry)

app = FastAPI(title="CIRS Feedback API", version="0.1.0")


def ensure_tables():
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
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
            CREATE SCHEMA IF NOT EXISTS cirs;
            CREATE TABLE IF NOT EXISTS cirs.user_feedback (
              feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              item_type TEXT CHECK (item_type IN ('answer','module')) NOT NULL,
              item_id TEXT NOT NULL,
              rating SMALLINT CHECK (rating BETWEEN 1 AND 5),
              helpful BOOLEAN,
              flags JSONB,
              comments TEXT,
              created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS cirs.finetune_corpus (
              sample_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              source_item_type TEXT CHECK (source_item_type IN ('answer','module')) NOT NULL,
              source_item_id TEXT NOT NULL,
              prompt TEXT NOT NULL,
              target TEXT NOT NULL,
              citations JSONB,
              confidence DOUBLE PRECISION,
              alignment_coverage DOUBLE PRECISION,
              agreement_score DOUBLE PRECISION,
              rating SMALLINT,
              included BOOLEAN DEFAULT TRUE,
              created_at TIMESTAMPTZ DEFAULT NOW()
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


@app.post('/feedback/answer')
async def feedback_answer(body: AnswerFeedback = Body(...)):
    ensure_tables()
    if body.rating:
        feedback_counter.labels(type='answer', rating=str(body.rating)).inc()
    import os
    DB_URL = os.getenv('DB_URL')
    if DB_URL:
        try:
            import psycopg2, json
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO cirs.user_feedback (item_type, item_id, rating, helpful, flags, comments)
                VALUES ('answer', %s, %s, %s, %s, %s)
                """,
                (body.answer_id, body.rating, body.helpful, json.dumps(body.flags or {}), body.comments)
            )
            cur.close(); conn.close()
        except Exception:
            pass
    return {"ok": True}


@app.post('/feedback/module')
async def feedback_module(body: ModuleFeedback = Body(...)):
    ensure_tables()
    if body.rating:
        feedback_counter.labels(type='module', rating=str(body.rating)).inc()
    import os
    DB_URL = os.getenv('DB_URL')
    if DB_URL:
        try:
            import psycopg2, json
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO cirs.user_feedback (item_type, item_id, rating, helpful, flags, comments)
                VALUES ('module', %s, %s, %s, %s, %s)
                """,
                (body.module_id, body.rating, body.helpful, json.dumps(body.flags or {}), body.comments)
            )
            cur.close(); conn.close()
        except Exception:
            pass
    return {"ok": True}


@app.get('/history')
async def history(item_type: Optional[str] = Query(None), item_id: Optional[str] = Query(None)):
    import os
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"items": []}
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        if item_type and item_id:
            cur.execute("SELECT item_type, item_id, rating, helpful, flags, comments, created_at FROM cirs.user_feedback WHERE item_type=%s AND item_id=%s ORDER BY created_at DESC LIMIT 100", (item_type, item_id))
        else:
            cur.execute("SELECT item_type, item_id, rating, helpful, flags, comments, created_at FROM cirs.user_feedback ORDER BY created_at DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close(); conn.close()
        items = []
        for r in rows:
            items.append({
                "item_type": r[0], "item_id": r[1], "rating": r[2], "helpful": r[3], "flags": r[4], "comments": r[5], "created_at": r[6].isoformat() if r[6] else None
            })
        return {"items": items}
    except Exception:
        return {"items": []}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8014)
