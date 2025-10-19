from fastapi import FastAPI, Path, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from prometheus_client import CONTENT_TYPE_LATEST
from .metrics_collector import render_prometheus
from .provenance import resolve_answer_provenance

app = FastAPI(title="CIRS Monitoring & Provenance", version="0.1.0")


class RetrievedItem(BaseModel):
    chunk_id: Optional[str] = None
    source_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: Optional[str] = None
    score: Optional[float] = None
    confidence_medical: Optional[float] = None
    validation_confidence: Optional[float] = None


class ProvenanceIn(BaseModel):
    retrieved: List[RetrievedItem]


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/metrics")
async def metrics():
    data, ctype = render_prometheus()
    return app.response_class(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/provenance/{answer_id}")
async def provenance(answer_id: str = Path(...), body: ProvenanceIn = Body(...)):
    prov = resolve_answer_provenance(answer_id, [r.dict() for r in body.retrieved])
    return prov


@app.post("/reprocess/{source_id}")
async def reprocess(source_id: str):
    # Placeholder: In real pipeline, enqueue a job spanning ASR->Validation->Chunking->Embedding
    return {"ok": True, "source_id": source_id, "status": "queued"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
