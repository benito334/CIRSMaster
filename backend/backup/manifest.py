import os
import json
import hashlib
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        return out
    except Exception:
        return "unknown"


def _env_fingerprint(env_path: Path = Path(".env")) -> str:
    try:
        data = env_path.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        return f"sha256:{h[:12]}..."
    except Exception:
        return "sha256:unknown"


def build_manifest(snapshot_id: str, models: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "snapshot_id": snapshot_id,
        "git_commit": _git_commit(),
        "compose_images": {},
        "models": models or {},
        "env_fingerprint": _env_fingerprint(),
        "cuda_driver": os.getenv("NVIDIA_DRIVER_VERSION", "unknown"),
        "hostname": socket.gethostname(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }


def write_manifest(path: Path, manifest: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return path
