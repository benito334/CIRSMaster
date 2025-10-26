import os
import tarfile
import hashlib
from pathlib import Path
from typing import List


def _iter_whitelist(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.exists():
            out.append(pp)
    return out


def pack_artifacts(paths: List[str], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out_path, "w:gz") as tar:
        for p in _iter_whitelist(paths):
            tar.add(p, arcname=str(p))
    return out_path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()
