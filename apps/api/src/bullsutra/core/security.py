import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from bullsutra.core.config import settings
from bullsutra.core.errors import Unauthorized

hasher = PasswordHasher()

@dataclass
class Principal:
    kind: Literal["user", "api_key"]
    id: str
    role: str

def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    return hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError):
        return False

def create_access_token(user_id: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str, role: str = "admin") -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)
    payload = {
        "sub": user_id,
        "role": role,
        "typ": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str, expected_typ: str = "access") -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("typ") != expected_typ:
            raise Unauthorized("Invalid token type")
        return payload
    except jwt.PyJWTError as e:
        raise Unauthorized(f"Invalid or expired token: {str(e)}")

def generate_api_key() -> tuple[str, str, str]:
    """Generates (raw_key, key_prefix, key_hash)."""
    raw_key = "bsk_" + secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]
    key_hash = hash_api_key(raw_key)
    return raw_key, key_prefix, key_hash

def hash_api_key(raw_key: str) -> str:
    to_hash = settings.API_KEY_PEPPER + raw_key
    return hashlib.sha256(to_hash.encode()).hexdigest()
