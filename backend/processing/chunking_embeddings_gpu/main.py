import argparse
import json
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from config import (
    INPUT_PATH,
    OUTPUT_PATH,
    RUN_TAG,
    CHUNK_SIZE_TOKENS,
    EMBED_MODEL,
    EMBED_BATCH_SIZE,
    QDRANT_URL,
    QDRANT_COLLECTION,
    DB_URL,
    EMBEDDED_INDEX,
)
from chunker import chunk_validated_segments, write_chunks_json
from embedder import embed_and_upsert


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def timestamp_tag() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def load_index() -> Dict[str, Any]:
    p = Path(EMBEDDED_INDEX)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_index(idx: Dict[str, Any]):
    p = Path(EMBEDDED_INDEX)
    ensure_dir(p.parent)
    p.write_text(json.dumps(idx, indent=2), encoding="utf-8")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_validated(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(".json"):
                files.append(Path(dirpath) / fn)
    return sorted(files)


def maybe_write_db(chunks: List[Dict[str, Any]], model: str, dim: int) -> bool:
    if not DB_URL:
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        # Insert chunks if not exist (idempotent on primary key)
        for c in chunks:
            sql_chunks = (
                "INSERT INTO cirs.chunks (chunk_id, parent_type, parent_id, source_id, text, start_time, end_time, page, section_path, topic_tags, entities) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (chunk_id) DO NOTHING"
            )
            cur.execute(
                sql_chunks,
                (
                    c.get("chunk_id"),
                    "transcript",
                    None,
                    c.get("source_id"),
                    c.get("text"),
                    c.get("start_time"),
                    c.get("end_time"),
                    None,
                    None,
                    json.dumps(c.get("topic_tags", [])),
                    json.dumps(c.get("entities", [])),
                ),
            )
            sql_emb = (
                "INSERT INTO cirs.embeddings (chunk_id, model, dim) VALUES (%s, %s, %s) "
                "ON CONFLICT (chunk_id) DO NOTHING"
            )
            cur.execute(sql_emb, (c.get("chunk_id"), model, dim))
        cur.close()
        conn.close()
        return True
    except Exception:
        return False


def process_file(path: Path, run_tag: str) -> Optional[Dict[str, Any]]:
    idx = load_index()
    h = file_hash(path)
    if idx.get(h):
        return None
    try:
        segments = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(segments, dict) and "segments" in segments:
            segments = segments["segments"]
        if not isinstance(segments, list):
            return None
        # For now, source_id is unknown; pipeline can pass via filename map later
        chunks = chunk_validated_segments(segments, source_id=None)
        out_dir = Path(OUTPUT_PATH) / run_tag
        out_path = write_chunks_json(out_dir, path.stem, chunks)
        # Embed and upsert to Qdrant
        emb_res = embed_and_upsert(chunks)
        # Optional DB rows
        maybe_write_db(chunks, model=EMBED_MODEL, dim=emb_res.dim)
        idx[h] = {"in": str(path), "chunks": str(out_path), "count": len(chunks), "dim": emb_res.dim, "run_tag": run_tag}
        save_index(idx)
        return {"in": str(path), "out": str(out_path), "count": len(chunks), "dim": emb_res.dim}
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Chunking & Embeddings GPU Service")
    parser.add_argument("--input", type=str, default=INPUT_PATH)
    parser.add_argument("--tag", type=str, default=None)
    args = parser.parse_args()

    in_root = Path(args.input)
    if not in_root.exists():
        print(f"Input not found: {in_root}")
        sys.exit(1)

    run_tag = args.tag or RUN_TAG or timestamp_tag()
    files = scan_validated(in_root)
    if not files:
        print("No validated transcripts found.")
        return

    total_chunks = 0
    for f in tqdm(files, desc="Chunk+Embed"):
        res = process_file(f, run_tag)
        if res:
            total_chunks += int(res.get("count", 0))

    print(json.dumps({
        "run_tag": run_tag,
        "files": len(files),
        "chunks": total_chunks,
        "embed_model": EMBED_MODEL,
        "batch": EMBED_BATCH_SIZE,
        "qdrant": QDRANT_URL,
        "collection": QDRANT_COLLECTION
    }, indent=2))


if __name__ == "__main__":
    main()
