import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bullsutra.db.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin')", name="ck_users_role_admin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        CheckConstraint("role IN ('admin')", name="ck_api_keys_role_admin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[Optional[User]] = relationship("User", back_populates="api_keys")
