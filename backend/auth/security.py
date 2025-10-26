import os
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, List, Optional
import jwt
from passlib.context import CryptContext
from config import JWT_ALG, JWT_SECRET, ACCESS_TTL_MIN, REFRESH_TTL_DAYS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def issue_tokens(user_id: str, tenant_id: str, role: str, scopes: List[str]) -> Dict[str, str]:
    now = int(time.time())
    access_exp = now + ACCESS_TTL_MIN * 60
    refresh_exp = now + REFRESH_TTL_DAYS * 24 * 3600
    access = jwt.encode({
        'sub': user_id,
        'tenant_id': tenant_id,
        'role': role,
        'scopes': scopes,
        'iat': now,
        'exp': access_exp
    }, JWT_SECRET, algorithm=JWT_ALG)
    refresh = jwt.encode({
        'sub': user_id,
        'tenant_id': tenant_id,
        'type': 'refresh',
        'iat': now,
        'exp': refresh_exp
    }, JWT_SECRET, algorithm=JWT_ALG)
    return {'access_token': access, 'refresh_token': refresh}


def verify_jwt(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
