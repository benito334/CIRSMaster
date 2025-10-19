from pathlib import Path
from typing import List, Dict, Any
import json

from config import BM25_INDEX_PATH, CHUNKS_ROOT, TOP_K_LEXICAL


SCHEMA_FIELDS = {
    "chunk_id": str,
    "text": str,
    "source_id": str,
    "start_time": float,
    "end_time": float,
}


def _schema():
    from whoosh.fields import Schema, ID, TEXT, STORED, NUMERIC
    return Schema(
        chunk_id=ID(stored=True, unique=True),
        text=TEXT(stored=True),
        source_id=ID(stored=True),
        start_time=NUMERIC(float, stored=True),
        end_time=NUMERIC(float, stored=True),
        payload=STORED,
    )


def rebuild_index(index_dir: Path = Path(BM25_INDEX_PATH), chunks_root: Path = Path(CHUNKS_ROOT)) -> int:
    index_dir.mkdir(parents=True, exist_ok=True)
    from whoosh import index

    if index.exists_in(str(index_dir)):
        ix = index.open_dir(str(index_dir))
        writer = ix.writer(limitmb=256)
    else:
        ix = index.create_in(str(index_dir), _schema())
        writer = ix.writer(limitmb=256)

    added = 0
    for p in chunks_root.rglob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            for c in data:
                chunk_id = c.get("chunk_id")
                text = c.get("text", "")
                payload = {
                    "chunk_id": chunk_id,
                    "source_id": c.get("source_id"),
                    "text": text,
                    "start_time": c.get("start_time"),
                    "end_time": c.get("end_time"),
                    "entities": c.get("entities", []),
                    "topic_tags": c.get("topic_tags", []),
                }
                writer.update_document(
                    chunk_id=str(chunk_id),
                    text=text,
                    source_id=str(c.get("source_id")) if c.get("source_id") else "",
                    start_time=float(c.get("start_time") or 0.0),
                    end_time=float(c.get("end_time") or 0.0),
                    payload=payload,
                )
                added += 1
        except Exception:
            continue
    writer.commit()
    return added


def lexical_search(query: str, top_k: int = TOP_K_LEXICAL, index_dir: Path = Path(BM25_INDEX_PATH)) -> List[Dict[str, Any]]:
    from whoosh import index
    from whoosh.qparser import MultifieldParser

    if not index.exists_in(str(index_dir)):
        return []
    ix = index.open_dir(str(index_dir))
    with ix.searcher() as searcher:
        parser = MultifieldParser(["text"], schema=ix.schema)
        q = parser.parse(query)
        results = searcher.search(q, limit=top_k)
        out: List[Dict[str, Any]] = []
        for r in results:
            payload = r.get("payload") or {}
            out.append({
                "chunk_id": payload.get("chunk_id") or r["chunk_id"],
                "score": float(r.score) if r.score is not None else None,
                "source_id": payload.get("source_id"),
                "text": payload.get("text") or r.get("text", ""),
                "start_time": payload.get("start_time"),
                "end_time": payload.get("end_time"),
                "entities": payload.get("entities", []),
                "topic_tags": payload.get("topic_tags", []),
                "provenance": "bm25",
            })
        return out
