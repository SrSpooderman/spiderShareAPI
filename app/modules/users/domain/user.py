from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


ROLE_RANKS: dict[UserRole, int] = {
    UserRole.USER: 1,
    UserRole.ADMIN: 2,
    UserRole.SUPER_ADMIN: 3,
}


def has_role_at_least(actual_role: UserRole, required_role: UserRole) -> bool:
    return ROLE_RANKS[actual_role] >= ROLE_RANKS[required_role]


def can_create_user_with_role(creator_role: UserRole, target_role: UserRole) -> bool:
    if target_role == UserRole.SUPER_ADMIN:
        return False

    if creator_role == UserRole.SUPER_ADMIN:
        return target_role in {UserRole.ADMIN, UserRole.USER}

    if creator_role == UserRole.ADMIN:
        return target_role == UserRole.USER

    return False


def can_manage_user(manager_role: UserRole, target_role: UserRole) -> bool:
    return ROLE_RANKS[manager_role] > ROLE_RANKS[target_role]


@dataclass
class User:
    id: UUID
    username: str
    display_name: str | None
    bio: str | None
    avatar_image: bytes | None
    password_hash: str
    ldap: bool
    role: UserRole
    is_active: bool
    last_seen_version: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

@dataclass
class UserCreate:
    username: str
    display_name: str | None
    bio: str | None
    avatar_image: bytes | None
    password_hash: str
    ldap: bool
    role: UserRole = UserRole.USER
