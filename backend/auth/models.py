from typing import Optional
import os
import psycopg2

DDL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS cirs;
CREATE TABLE IF NOT EXISTS cirs.tenants (
  tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE EXTENSION IF NOT EXISTS citext;
CREATE TABLE IF NOT EXISTS cirs.users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES cirs.tenants(tenant_id) ON DELETE CASCADE,
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name TEXT,
  role TEXT CHECK (role IN ('admin','editor','viewer','ingester','monitor')) NOT NULL DEFAULT 'viewer',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS cirs.api_keys (
  key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES cirs.tenants(tenant_id) ON DELETE CASCADE,
  user_id UUID REFERENCES cirs.users(user_id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  hashed_key TEXT NOT NULL,
  scopes TEXT[] NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  revoked BOOLEAN DEFAULT FALSE
);
"""


def ensure_schema(db_url: Optional[str] = None):
    url = db_url or os.getenv('DB_URL')
    if not url:
        raise RuntimeError('DB_URL not set')
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(DDL)
    cur.close(); conn.close()


def bootstrap_default_tenant_and_admin(email: str, password_hash: str, tenant_name: str = 'default'):
    url = os.getenv('DB_URL')
    conn = psycopg2.connect(url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT tenant_id FROM cirs.tenants WHERE name=%s", (tenant_name,))
    row = cur.fetchone()
    if row:
        tenant_id = row[0]
    else:
        cur.execute("INSERT INTO cirs.tenants (name) VALUES (%s) RETURNING tenant_id", (tenant_name,))
        tenant_id = cur.fetchone()[0]
    cur.execute("SELECT user_id FROM cirs.users WHERE email=%s", (email,))
    if not cur.fetchone():
        cur.execute("INSERT INTO cirs.users (tenant_id, email, password_hash, display_name, role) VALUES (%s,%s,%s,%s,'admin')",
                    (tenant_id, email, password_hash, 'Admin'))
    cur.close(); conn.close()
