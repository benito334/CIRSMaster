from typing import List, Dict, Any
from fastapi import FastAPI, Query
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

from config import (
    VECTOR_WEIGHT, LEXICAL_WEIGHT, TOP_K_VECTOR, TOP_K_LEXICAL,
    BM25_INDEX_PATH, CHUNKS_ROOT
)
from vector import vector_search
from lexical import lexical_search, rebuild_index

app = FastAPI(title="CIRS Hybrid Retriever", version="0.1.0")


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: List[Dict[str, Any]]


def _rrf(results: List[Dict[str, Any]]) -> Dict[str, float]:
    # Reciprocal rank fusion per list
    r = {}
    for rank, item in enumerate(results, start=1):
        cid = item.get("chunk_id")
        r[cid] = r.get(cid, 0.0) + 1.0 / (60.0 + rank)
    return r


def _weighted_merge(vec: List[Dict[str, Any]], lex: List[Dict[str, Any]], alpha: float) -> List[Dict[str, Any]]:
    # Use RRF for stability, then weight
    r_vec = _rrf(vec)
    r_lex = _rrf(lex)
    ids = set(r_vec.keys()) | set(r_lex.keys())
    by_id = {}
    for cid in ids:
        v = r_vec.get(cid, 0.0)
        l = r_lex.get(cid, 0.0)
        score = alpha * v + (1 - alpha) * l
        by_id[cid] = score

    # Collect payloads from whichever list has the item
    payload = {}
    for item in vec + lex:
        cid = item.get("chunk_id")
        if cid not in payload:
            payload[cid] = item

    ranked = sorted(ids, key=lambda x: by_id[x], reverse=True)
    return [{**payload[i], "score": by_id[i]} for i in ranked]


@app.get("/search", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1), mode: str = Query("hybrid", pattern="^(vector|lexical|hybrid)$")):
    vec_res: List[Dict[str, Any]] = []
    lex_res: List[Dict[str, Any]] = []

    if mode in ("vector", "hybrid"):
        vec_res = vector_search(q, top_k=TOP_K_VECTOR)
    if mode in ("lexical", "hybrid"):
        lex_res = lexical_search(q, top_k=TOP_K_LEXICAL)

    if mode == "vector":
        ranked = vec_res
    elif mode == "lexical":
        ranked = lex_res
    else:
        ranked = _weighted_merge(vec_res, lex_res, alpha=VECTOR_WEIGHT)

    return SearchResponse(query=q, mode=mode, results=ranked)


@app.post("/rebuild-index")
async def rebuild():
    added = rebuild_index(Path(BM25_INDEX_PATH), Path(CHUNKS_ROOT))
    return {"ok": True, "added": added, "index": BM25_INDEX_PATH}


@app.get("/health")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
