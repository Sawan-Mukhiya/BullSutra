from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class MeResponse(BaseModel):
    id: str
    email: Optional[str] = None
    role: str
    kind: Literal["user", "api_key"]

class CreateApiKeyRequest(BaseModel):
    name: str

class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    key: str
    created_at: datetime

class ApiKeySummary(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
