from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio

from orchestrator import answer_query, retrieve_chunks
from curriculum_builder import build_module

app = FastAPI(title="CIRS Chat Orchestrator", version="0.1.0")


class ChatIn(BaseModel):
    query: str
    mode: Optional[str] = "hybrid"


class ModuleIn(BaseModel):
    topic: str
    mode: Optional[str] = "hybrid"
    top_k: Optional[int] = 8


@app.post("/chat")
async def chat(payload: ChatIn):
    result = await answer_query(payload.query, mode=payload.mode)
    return result


@app.post("/module")
async def module(payload: ModuleIn):
    chunks = await retrieve_chunks(payload.topic, mode=payload.mode, top_k=payload.top_k)
    mod = build_module(payload.topic, chunks)
    return mod


@app.get("/health")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
