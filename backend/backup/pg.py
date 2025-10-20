import os
import subprocess
import gzip
import shutil
from pathlib import Path
from .config import PG_HOST, PG_USER, PG_DB, PG_PORT


def dump_postgres(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / 'pg_dump.sql.gz'
    pgurl = os.getenv('DB_URL')
    if pgurl:
        # Use psql-compatible URL: e.g., postgresql://user:pass@host:5432/db
        dump_cmd = [
            'pg_dump', pgurl
        ]
    else:
        dump_cmd = [
            'pg_dump', '-h', PG_HOST, '-p', str(PG_PORT), '-U', PG_USER, PG_DB
        ]
    env = os.environ.copy()
    # Expect PGPASSWORD in env if needed
    proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    with gzip.open(out, 'wb') as gz:
        assert proc.stdout is not None
        shutil.copyfileobj(proc.stdout, gz)
    _, err = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {err.decode('utf-8', 'ignore')}")
    return out
