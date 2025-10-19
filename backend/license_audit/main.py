from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from prometheus_client import Counter, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
import os
from .auditor import scan_path, to_policy

registry = CollectorRegistry()
restricted_counter = Counter('restricted_sources_total', 'Restricted sources detected', ['license'], registry=registry)

app = FastAPI(title="CIRS License Audit", version="0.1.0")

class ScanRequest(BaseModel):
    path: str


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
            CREATE SCHEMA IF NOT EXISTS cirs;
            CREATE TABLE IF NOT EXISTS cirs.license_registry (
              source_id TEXT PRIMARY KEY,
              license TEXT,
              license_type TEXT,
              usage_restrictions TEXT,
              verified BOOLEAN DEFAULT FALSE,
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


@app.post('/license/scan')
async def license_scan(req: ScanRequest = Body(...)):
    ensure_tables()
    results = scan_path(req.path)
    DB_URL = os.getenv('DB_URL')
    out: List[Dict[str, Any]] = []
    if DB_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DB_URL)
            conn.autocommit = True
            cur = conn.cursor()
            for r in results:
                pol = to_policy(r['license'])
                out.append({**r, **pol})
                if pol['license_type'] in ('restricted','prohibited'):
                    restricted_counter.labels(license=r['license']).inc()
                cur.execute(
                    """
                    INSERT INTO cirs.license_registry (source_id, license, license_type, usage_restrictions, verified)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (source_id) DO UPDATE SET license=EXCLUDED.license, license_type=EXCLUDED.license_type, usage_restrictions=EXCLUDED.usage_restrictions
                    """,
                    (r['source_id'], r['license'], pol['license_type'], pol['usage_restrictions'], False)
                )
            cur.close(); conn.close()
        except Exception:
            out = results
    else:
        out = results
    return {"items": out}


@app.get('/license/report')
async def license_report():
    DB_URL = os.getenv('DB_URL')
    if not DB_URL:
        return {"items": []}
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT source_id, license, license_type, usage_restrictions, verified, created_at FROM cirs.license_registry ORDER BY created_at DESC LIMIT 1000")
        rows = cur.fetchall(); cur.close(); conn.close()
        items = []
        for r in rows:
            items.append({
                'source_id': r[0], 'license': r[1], 'license_type': r[2], 'usage_restrictions': r[3], 'verified': r[4], 'created_at': r[5].isoformat() if r[5] else None
            })
        return {"items": items}
    except Exception:
        return {"items": []}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8017)
