import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.core.config import settings
from bullsutra.core.errors import Unauthorized, Forbidden, Conflict, ValidationError
from bullsutra.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    Principal,
)
from bullsutra.db.session import get_db
from bullsutra.db.repositories import users, api_keys
from bullsutra.api.deps import require_admin, get_principal_optional
from bullsutra.schemas.auth import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    RefreshRequest,
    MeResponse,
    CreateApiKeyRequest,
    ApiKeyCreatedResponse,
    ApiKeySummary,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await users.get_by_email(db, req.email)
    if not user or not verify_password(req.password, user.password_hash) or not user.is_active:
        raise Unauthorized("Invalid email or password")

    await users.update_last_login(db, user.id)
    await db.commit()

    access_tok = create_access_token(str(user.id), role=user.role)
    refresh_tok = create_refresh_token(str(user.id), role=user.role)
    return TokenResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(req: SignupRequest, db: AsyncSession = Depends(get_db)):
    if len(req.password) < 8:
        raise ValidationError("Password must be at least 8 characters long")

    existing = await users.get_by_email(db, req.email)
    if existing:
        raise Conflict("An account with this email address already exists")

    pwd_hash = hash_password(req.password)
    user = await users.create_user(db, req.email, pwd_hash, role="admin")
    await db.commit()

    access_tok = create_access_token(str(user.id), role=user.role)
    refresh_tok = create_refresh_token(str(user.id), role=user.role)
    return TokenResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token, expected_typ="refresh")
    user_id = payload.get("sub")
    if not user_id:
        raise Unauthorized("Invalid refresh token")

    user = await users.get_by_id(db, uuid.UUID(user_id))
    if not user or not user.is_active:
        raise Unauthorized("User inactive or not found")

    access_tok = create_access_token(str(user.id), role=user.role)
    refresh_tok = create_refresh_token(str(user.id), role=user.role)
    return TokenResponse(
        access_token=access_tok,
        refresh_token=refresh_tok,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
    )

@router.get("/me", response_model=MeResponse)
async def get_me(p: Principal = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    email = None
    if p.kind == "user":
        user = await users.get_by_id(db, uuid.UUID(p.id))
        email = user.email if user else None
    return MeResponse(
        id=p.id,
        email=email,
        role=p.role,
        kind=p.kind,
    )

@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: CreateApiKeyRequest,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if p.kind != "user":
        raise Forbidden("Only user accounts can create API keys")

    raw_key, prefix, k_hash = generate_api_key()
    key_obj = await api_keys.create_key(
        db,
        name=req.name,
        key_prefix=prefix,
        key_hash=k_hash,
        created_by=uuid.UUID(p.id),
        role="admin"
    )
    await db.commit()
    return ApiKeyCreatedResponse(
        id=str(key_obj.id),
        name=key_obj.name,
        key_prefix=key_obj.key_prefix,
        key=raw_key,
        created_at=key_obj.created_at,
    )

@router.get("/api-keys", response_model=dict[str, list[ApiKeySummary]])
async def list_api_keys(p: Principal = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    keys = await api_keys.list_keys(db)
    items = [
        ApiKeySummary(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            revoked_at=k.revoked_at,
        )
        for k in keys
    ]
    return {"items": items}

@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if p.kind != "user":
        raise Forbidden("Only user accounts can revoke API keys")
    await api_keys.revoke_key(db, key_id)
    await db.commit()
