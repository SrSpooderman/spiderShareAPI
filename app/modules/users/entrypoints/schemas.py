from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.users.domain.user import User, UserRole


class UserResponse(BaseModel):
    id: UUID
    username: str
    display_name: str | None
    bio: str | None
    has_avatar: bool
    ldap: bool
    role: UserRole
    is_active: bool
    last_seen_version: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            has_avatar=user.avatar_image is not None,
            ldap=user.ldap,
            role=user.role,
            is_active=user.is_active,
            last_seen_version=user.last_seen_version,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, min_length=1, max_length=500)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username", mode="before")
    @classmethod
    def username_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value

        username = value.strip()
        if not username:
            raise ValueError("username cannot be blank")
        return username

    @field_validator("display_name", "bio", mode="before")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value

        text = value.strip()
        if not text:
            raise ValueError("value cannot be blank")
        return text


class PasswordChangeRequest(BaseModel):
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
