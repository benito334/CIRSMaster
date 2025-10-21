import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras as extras

from config import DB_URL, PORT
from models import init_db

app = FastAPI(title="CIRS Pipeline Controller", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    stages: List[str]
    overwrite_existing: bool = False
    resume: bool = True
    scope: Optional[str] = None  # all | source_type | files
    files: Optional[List[str]] = None  # list of file_ids


class UpdateStatusRequest(BaseModel):
    file_id: str
    stage: str
    done: bool = False
    error: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    run_tag: Optional[str] = None


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.get("/metrics")
def metrics():
    # Minimal placeholder; integrate Prometheus client in future
    return {"pipeline_controller_up": 1}


@app.get("/status/all")
def status_all():
    if not DB_URL:
        return {"items": []}
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=extras.RealDictCursor)
    cur.execute("SELECT * FROM cirs.pipeline_status ORDER BY last_update DESC LIMIT 500")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"items": rows}


@app.get("/logs/{file_id}")
def logs(file_id: str):
    # Placeholder: in the future, read from structured logs
    return {"file_id": file_id, "logs": ["No logs available yet"], "time": datetime.utcnow().isoformat() + "Z"}


@app.post("/status/update")
def status_update(payload: UpdateStatusRequest):
    if not DB_URL:
        raise HTTPException(500, "DB not configured")
    try:
        fid = uuid.UUID(payload.file_id)
    except Exception:
        raise HTTPException(400, "invalid file_id")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Upsert row
    cols = [
        "file_id", "filename", "file_type", "run_tag",
        "asr_done", "validation_done", "embedding_done",
        "asr_error", "validation_error", "embedding_error",
        "last_update"
    ]
    values = {
        "file_id": str(fid),
        "filename": payload.filename,
        "file_type": payload.file_type,
        "run_tag": payload.run_tag,
        "asr_done": None,
        "validation_done": None,
        "embedding_done": None,
        "asr_error": None,
        "validation_error": None,
        "embedding_error": None,
        "last_update": datetime.utcnow(),
    }
    stage = (payload.stage or "").lower()
    if stage == "asr":
        values["asr_done"] = payload.done
        values["asr_error"] = payload.error
    elif stage == "validate":
        values["validation_done"] = payload.done
        values["validation_error"] = payload.error
    elif stage == "embed":
        values["embedding_done"] = payload.done
        values["embedding_error"] = payload.error

    # Upsert using ON CONFLICT
    sql = (
        "INSERT INTO cirs.pipeline_status (" + ",".join(cols) + ") VALUES (" + ",".join(["%s"]*len(cols)) + ") "
        "ON CONFLICT (file_id) DO UPDATE SET "
        "filename = EXCLUDED.filename, file_type = EXCLUDED.file_type, run_tag = EXCLUDED.run_tag, "
        "asr_done = COALESCE(EXCLUDED.asr_done, cirs.pipeline_status.asr_done), "
        "validation_done = COALESCE(EXCLUDED.validation_done, cirs.pipeline_status.validation_done), "
        "embedding_done = COALESCE(EXCLUDED.embedding_done, cirs.pipeline_status.embedding_done), "
        "asr_error = COALESCE(EXCLUDED.asr_error, cirs.pipeline_status.asr_error), "
        "validation_error = COALESCE(EXCLUDED.validation_error, cirs.pipeline_status.validation_error), "
        "embedding_error = COALESCE(EXCLUDED.embedding_error, cirs.pipeline_status.embedding_error), "
        "last_update = EXCLUDED.last_update"
    )
    cur.execute(sql, [
        values["file_id"], values["filename"], values["file_type"], values["run_tag"],
        values["asr_done"], values["validation_done"], values["embedding_done"],
        values["asr_error"], values["validation_error"], values["embedding_error"],
        values["last_update"],
    ])
    cur.close()
    conn.close()
    return {"status": "ok"}


@app.post("/process")
def process(req: ProcessRequest):
    # Stub: queueing/trigger logic would invoke services or enqueue jobs
    # Return an ack with requested stages and scope
    return {
        "accepted": True,
        "stages": req.stages,
        "overwrite_existing": req.overwrite_existing,
        "resume": req.resume,
        "scope": req.scope,
        "files": req.files or [],
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/reprocess/{file_id}")
def reprocess(file_id: str, req: ProcessRequest):
    # Stub: same as process but scoped to a single file
    try:
        uuid.UUID(file_id)
    except Exception:
        raise HTTPException(400, "invalid file_id")
    return {
        "accepted": True,
        "file_id": file_id,
        "stages": req.stages,
        "submitted_at": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
