from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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
    username: str | None = None
    display_name: str | None = None
    bio: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str | None = None
    new_password: str
