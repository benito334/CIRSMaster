from fastapi import FastAPI, Body, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
from prometheus_client import Counter, Summary, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
import os, json, subprocess

from .config import BACKUP_ROOT, INCLUDE_DIRS
from .pg import dump_postgres
from .qdrant import create_global_snapshot
from .artifacts import pack_artifacts, sha256_file
from .manifest import build_manifest, write_manifest

registry = CollectorRegistry()
backup_success_total = Counter('backup_success_total', 'Total successful backups', registry=registry)
backup_failure_total = Counter('backup_failure_total', 'Total failed backups', registry=registry)
restore_success_total = Counter('restore_success_total', 'Total successful restores', registry=registry)
backup_last_duration_seconds = Summary('backup_last_duration_seconds', 'Duration of last backup (s)', registry=registry)

app = FastAPI(title="CIRS Backup Service", version="0.1.0")

class RunRequest(BaseModel):
    label: Optional[str] = None

class RestoreRequest(BaseModel):
    snapshot_id: str
    parts: List[str] = ["pg","qdrant","artifacts"]


def _snapshot_id() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%MZ')


def _checksums_write(folder: Path, files: List[Path]):
    lines = []
    for f in files:
        if f.exists():
            lines.append(f"{sha256_file(f)}  {f.name}")
    (folder / 'checksums.sha256').write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')


def _retention_rotate():
    # Simple retention: keep last N by mtime; more advanced daily/weekly/monthly can be added later
    keep = int(os.getenv('BACKUP_KEEP_LAST', '14'))
    root = Path(BACKUP_ROOT)
    if not root.exists():
        return
    dirs = [d for d in root.iterdir() if d.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for d in dirs[keep:]:
        try:
            for sub in d.rglob('*'):
                if sub.is_file():
                    sub.unlink(missing_ok=True)
            for sub in sorted(d.rglob('*'), reverse=True):
                if sub.is_dir():
                    sub.rmdir()
            d.rmdir()
        except Exception:
            continue


@app.get('/health')
async def health():
    return {"ok": True}


@app.get('/metrics')
async def metrics():
    data = generate_latest(registry)
    return app.response_class(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get('/backup/list')
async def list_backups(limit: int = Query(20)):
    root = Path(BACKUP_ROOT)
    items = []
    if root.exists():
        for d in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)[:limit]:
            items.append({"snapshot_id": d.name})
    return {"items": items}


@app.post('/backup/run')
@backup_last_duration_seconds.time()
async def backup_run(req: RunRequest = Body(default=RunRequest())):
    sid = _snapshot_id()
    folder = Path(BACKUP_ROOT) / sid
    folder.mkdir(parents=True, exist_ok=True)
    try:
        pg_path = dump_postgres(folder)
        qdrant_path = create_global_snapshot(folder / 'qdrant_snapshot')
        data_tar = pack_artifacts(INCLUDE_DIRS, folder / 'data_artifacts.tar.gz')
        manifest = build_manifest(sid)
        write_manifest(folder / 'manifest.json', manifest)
        _checksums_write(folder, [pg_path, data_tar, qdrant_path])
        backup_success_total.inc()
        _retention_rotate()
        return {"ok": True, "snapshot_id": sid}
    except Exception as e:
        backup_failure_total.inc()
        return app.response_class(status_code=500, content=json.dumps({"ok": False, "error": str(e)}), media_type='application/json')


@app.post('/backup/restore')
async def backup_restore(req: RestoreRequest):
    folder = Path(BACKUP_ROOT) / req.snapshot_id
    if not folder.exists():
        return app.response_class(status_code=404, content=json.dumps({"ok": False, "error": "snapshot not found"}), media_type='application/json')
    try:
        if 'pg' in req.parts:
            pg_dump_gz = folder / 'pg_dump.sql.gz'
            if pg_dump_gz.exists():
                # pipe gunzip -> psql using DB_URL
                db_url = os.getenv('DB_URL')
                if not db_url:
                    raise RuntimeError('DB_URL not set for restore')
                cmd = f"gunzip -c '{pg_dump_gz}' | psql '{db_url}'"
                subprocess.check_call(cmd, shell=True)
        if 'artifacts' in req.parts:
            tar_path = folder / 'data_artifacts.tar.gz'
            if tar_path.exists():
                subprocess.check_call(f"tar -xzvf '{tar_path}' -C /", shell=True)
        # Qdrant restore flow varies by deployment; left as manual step
        restore_success_total.inc()
        return {"ok": True}
    except Exception as e:
        return app.response_class(status_code=500, content=json.dumps({"ok": False, "error": str(e)}), media_type='application/json')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', '8018')))
