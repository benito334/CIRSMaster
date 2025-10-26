import os
from typing import List, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
import jwt

ALG = os.getenv("AUTH_JWT_ALG", "HS256")
SECRET = os.getenv("AUTH_JWT_SECRET", "change_me")

class AuthContext:
    def __init__(self, claims: Dict[str, Any]):
        self.sub: str = claims.get('sub')
        self.tenant_id: str = claims.get('tenant_id')
        self.role: str = claims.get('role')
        self.scopes: List[str] = claims.get('scopes', [])
        self.claims = claims


def verify_jwt_header(authorization: Optional[str] = Header(None)) -> AuthContext:
    if not authorization or not authorization.lower().startswith('bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    token = authorization.split(' ', 1)[1]
    try:
        claims = jwt.decode(token, SECRET, algorithms=[ALG])
        return AuthContext(claims)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_auth(scopes: Optional[List[str]] = None):
    scopes = scopes or []
    def _dep(ctx: AuthContext = Depends(verify_jwt_header)) -> AuthContext:
        # simple scope check: any of required scopes must be present; 'admin:*' bypasses
        if ctx.role == 'admin':
            return ctx
        if scopes:
            if not any(s in ctx.scopes or s.split(':')[0]+':*' in ctx.scopes for s in scopes):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return ctx
    return _dep
