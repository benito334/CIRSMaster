import os
import requests
from pathlib import Path
from typing import List
from .config import QDRANT_URL


def create_collection_snapshot(collection: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    r = requests.post(f"{QDRANT_URL}/collections/{collection}/snapshots")
    r.raise_for_status()
    meta = r.json()
    # API returns path on server; we rely on mapped storage dir via volume
    # For simplicity, just record the metadata
    out = target_dir / f"{collection}_snapshot.json"
    out.write_text(r.text, encoding='utf-8')
    return out


def create_global_snapshot(target_dir: Path) -> Path:
    # Some Qdrant builds support service-level snapshot
    try:
        r = requests.post(f"{QDRANT_URL}/snapshots")
        r.raise_for_status()
        out = target_dir / "qdrant_snapshot.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(r.text, encoding='utf-8')
        return out
    except Exception:
        # Fallback: no-op
        out = target_dir / "qdrant_snapshot.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('{"status":"skipped"}', encoding='utf-8')
        return out
