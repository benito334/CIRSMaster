from fastapi import FastAPI, Body, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from prometheus_client import Counter, CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
import os, uuid
import psycopg2

from .config import DB_URL, PORT, TENANCY_DEFAULT_NAME
from .security import hash_password, verify_password, issue_tokens, verify_jwt
from .models import ensure_schema, bootstrap_default_tenant_and_admin

registry = CollectorRegistry()
auth_login_success_total = Counter('auth_login_success_total', 'Login successes', registry=registry)
auth_login_fail_total = Counter('auth_login_fail_total', 'Login failures', registry=registry)
auth_token_issued_total = Counter('auth_token_issued_total', 'Tokens issued', ['type'], registry=registry)

app = FastAPI(title="CIRS Auth Service", version="0.1.0")


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None
    tenant_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str


def _conn():
    if not DB_URL:
        raise RuntimeError('DB_URL not set')
    return psycopg2.connect(DB_URL)


@app.on_event("startup")
def on_startup():
    ensure_schema(DB_URL)
    # bootstrap default admin if env provided
    admin_email = os.getenv('BOOTSTRAP_ADMIN_EMAIL')
    admin_password = os.getenv('BOOTSTRAP_ADMIN_PASSWORD')
    if admin_email and admin_password:
        bootstrap_default_tenant_and_admin(admin_email, hash_password(admin_password), TENANCY_DEFAULT_NAME)


@app.get('/health')
async def health():
    return {"ok": True}


@app.get('/metrics')
async def metrics():
    data = generate_latest(registry)
    return app.response_class(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post('/auth/signup')
async def signup(req: SignupRequest = Body(...)):
    ensure_schema(DB_URL)
    tenant_name = req.tenant_name or TENANCY_DEFAULT_NAME
    conn = _conn(); conn.autocommit = True
    cur = conn.cursor()
    # ensure tenant
    cur.execute("SELECT tenant_id FROM cirs.tenants WHERE name=%s", (tenant_name,))
    row = cur.fetchone()
    if row:
        tenant_id = row[0]
    else:
        cur.execute("INSERT INTO cirs.tenants (name) VALUES (%s) RETURNING tenant_id", (tenant_name,))
        tenant_id = cur.fetchone()[0]
    # create user as viewer by default
    try:
        cur.execute("INSERT INTO cirs.users (tenant_id, email, password_hash, display_name, role) VALUES (%s,%s,%s,%s,'viewer') RETURNING user_id",
                    (tenant_id, req.email, hash_password(req.password), req.display_name or req.email))
        user_id = cur.fetchone()[0]
        cur.close(); conn.close()
        return {"ok": True, "user_id": str(user_id), "tenant_id": str(tenant_id)}
    except Exception as e:
        cur.close(); conn.close()
        raise HTTPException(status_code=400, detail="signup_failed")


@app.post('/auth/login')
async def login(req: LoginRequest = Body(...)):
    conn = _conn(); cur = conn.cursor()
    cur.execute("SELECT user_id, tenant_id, password_hash, role FROM cirs.users WHERE email=%s AND is_active=TRUE", (req.email,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        auth_login_fail_total.inc()
        raise HTTPException(status_code=401, detail="invalid_credentials")
    user_id, tenant_id, pw_hash, role = row
    if not verify_password(req.password, pw_hash):
        auth_login_fail_total.inc()
        raise HTTPException(status_code=401, detail="invalid_credentials")
    # simple role->scopes mapping
    role_scopes = {
        'admin': ['admin:*'],
        'editor': ['chat:*','retrieval:read','ingest:write'],
        'viewer': ['chat:read','retrieval:read','monitor:read'],
        'ingester': ['ingest:write','monitor:read'],
        'monitor': ['monitor:read']
    }
    scopes = role_scopes.get(role, [])
    tokens = issue_tokens(str(user_id), str(tenant_id), role, scopes)
    auth_login_success_total.inc(); auth_token_issued_total.labels(type='access').inc(); auth_token_issued_total.labels(type='refresh').inc()
    return tokens


@app.post('/auth/refresh')
async def refresh(req: RefreshRequest = Body(...)):
    try:
        claims = verify_jwt(req.refresh_token)
        if claims.get('type') != 'refresh':
            raise ValueError('not_refresh')
        # fetch role to map scopes again
        conn = _conn(); cur = conn.cursor()
        cur.execute("SELECT role FROM cirs.users WHERE user_id=%s AND is_active=TRUE", (claims.get('sub'),))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row:
            raise ValueError('user_not_found')
        role = row[0]
        role_scopes = {
            'admin': ['admin:*'],
            'editor': ['chat:*','retrieval:read','ingest:write'],
            'viewer': ['chat:read','retrieval:read','monitor:read'],
            'ingester': ['ingest:write','monitor:read'],
            'monitor': ['monitor:read']
        }
        scopes = role_scopes.get(role, [])
        tokens = issue_tokens(claims['sub'], claims['tenant_id'], role, scopes)
        auth_token_issued_total.labels(type='access').inc(); auth_token_issued_total.labels(type='refresh').inc()
        return tokens
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_refresh")


@app.get('/auth/whoami')
async def whoami(authorization: Optional[str] = None):
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=401, detail="missing_token")
    token = authorization.split(' ',1)[1]
    try:
        claims = verify_jwt(token)
        return {"user_id": claims.get('sub'), "tenant_id": claims.get('tenant_id'), "role": claims.get('role'), "scopes": claims.get('scopes', [])}
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_token")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT)
