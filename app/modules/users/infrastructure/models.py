from datetime import datetime

from sqlalchemy import Boolean, DateTime, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4

from app.shared.infrastructure.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda: str(uuid4()),)

    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)

    avatar_image: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    ldap: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False, server_default="local")
    oidc_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    oidc_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    oidc_groups: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")

    last_seen_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )
