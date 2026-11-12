import uuid
from typing import AsyncIterator, Optional
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.core.errors import Unauthorized, Forbidden
from bullsutra.core.security import Principal, decode_token, hash_api_key
from bullsutra.db.session import get_db
from bullsutra.db.repositories import users, api_keys

async def get_principal_optional(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[Principal]:
    # 1. API key auth
    if x_api_key:
        raw_key = x_api_key.strip()
        k_hash = hash_api_key(raw_key)
        key_obj = await api_keys.get_by_hash(db, k_hash)
        if not key_obj or not key_obj.is_active or key_obj.revoked_at is not None:
            raise Unauthorized("Invalid or revoked API key")
        await api_keys.update_last_used(db, key_obj.id)
        return Principal(kind="api_key", id=str(key_obj.id), role=key_obj.role)

    # 2. Bearer JWT auth
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            payload = decode_token(token, expected_typ="access")
            user_id = payload.get("sub")
            if not user_id:
                raise Unauthorized("Token missing subject")
            user = await users.get_by_id(db, uuid.UUID(user_id))
            if not user or not user.is_active:
                raise Unauthorized("User inactive or not found")
            return Principal(kind="user", id=str(user.id), role=user.role)
        raise Unauthorized("Invalid authorization header format")

    return None

async def require_admin(
    p: Optional[Principal] = Depends(get_principal_optional)
) -> Principal:
    if not p:
        raise Unauthorized("Authentication required")
    if p.role != "admin":
        raise Forbidden("Admin access required")
    return p
