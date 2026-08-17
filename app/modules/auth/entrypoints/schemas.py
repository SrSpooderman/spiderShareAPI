from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.auth.application.login import LoginResult
from app.modules.auth.application.register import PublicUser
from app.modules.users.domain.user import AuthProvider, User, UserRole


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER

    @field_validator("username", mode="before")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("username cannot be blank")
        return username


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("username cannot be blank")
        return username


class OidcAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str


class OidcCallbackRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: UUID
    username: str
    display_name: str | None
    bio: str | None
    ldap: bool
    auth_provider: AuthProvider
    oidc_subject: str | None
    oidc_email: str | None
    oidc_name: str | None
    oidc_groups: list[str]
    role: UserRole
    is_active: bool
    last_seen_version: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_public_user(cls, user: PublicUser) -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            ldap=user.ldap,
            auth_provider=user.auth_provider,
            oidc_subject=user.oidc_subject,
            oidc_email=user.oidc_email,
            oidc_name=user.oidc_name,
            oidc_groups=user.oidc_groups or [],
            role=user.role,
            is_active=user.is_active,
            last_seen_version=user.last_seen_version,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            ldap=user.ldap,
            auth_provider=user.auth_provider,
            oidc_subject=user.oidc_subject,
            oidc_email=user.oidc_email,
            oidc_name=user.oidc_name,
            oidc_groups=user.oidc_groups,
            role=user.role,
            is_active=user.is_active,
            last_seen_version=user.last_seen_version,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

    @classmethod
    def from_result(cls, result: LoginResult) -> "LoginResponse":
        return cls(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
            user=UserResponse.from_public_user(result.user),
        )
