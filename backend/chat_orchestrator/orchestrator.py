import json
from typing import List, Dict, Any, Tuple
import httpx
from datetime import datetime
from pathlib import Path

from .config import RETRIEVER_URL, TOP_K, SAVE_CONTEXT, CONTEXT_DIR
from .llm_client import generate_async


async def retrieve_chunks(query: str, mode: str = "hybrid", top_k: int = TOP_K) -> List[Dict[str, Any]]:
    params = {"q": query, "mode": mode}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(f"{RETRIEVER_URL}/search", params=params)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return results[:top_k]


def build_prompt(query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    header = (
        "You are a careful medical assistant. Answer ONLY using the provided CONTEXT. "
        "Cite sources inline as [source_id@t=start-end] and do not invent facts.\n\n"
        "CONTEXT:\n"
    )
    ctx_lines: List[str] = []
    citations: List[Dict[str, Any]] = []
    for i, c in enumerate(chunks, start=1):
        src = c.get("source_id") or "unknown"
        st = c.get("start_time")
        et = c.get("end_time")
        text = (c.get("text") or "").strip()
        ctx_lines.append(f"[{i}] ({src}@t={st}-{et})\n{text}\n")
        citations.append({
            "chunk_id": c.get("chunk_id"),
            "source_id": src,
            "start_time": st,
            "end_time": et,
        })
    user = f"\nUSER QUERY:\n{query}\n"
    prompt = header + "\n".join(ctx_lines) + user
    return prompt, citations


async def answer_query(query: str, mode: str = "hybrid") -> Dict[str, Any]:
    chunks = await retrieve_chunks(query, mode=mode)
    prompt, citations = build_prompt(query, chunks)

    # Optional: save context for debugging
    if SAVE_CONTEXT:
        Path(CONTEXT_DIR).mkdir(parents=True, exist_ok=True)
        tag = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        (Path(CONTEXT_DIR) / f"context_{tag}.json").write_text(
            json.dumps({"query": query, "mode": mode, "chunks": chunks}, indent=2), encoding="utf-8"
        )
        (Path(CONTEXT_DIR) / f"prompt_{tag}.txt").write_text(prompt, encoding="utf-8")

    completion = await generate_async(prompt)

    return {
        "query": query,
        "mode": mode,
        "answer": completion,
        "citations": citations,
        "confidence": None,  # placeholder; future scoring can be added
    }
