from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.auth.application.password_hasher import PasswordHasher
from app.modules.users.domain.ports import UserPersistenceConflictError, UserRepository
from app.modules.users.domain.user import AuthProvider, User, UserCreate, UserRole


class UsernameAlreadyExistsError(Exception):
    pass


@dataclass(frozen=True)
class RegisterUserCommand:
    username: str
    password: str
    role: UserRole = UserRole.USER


@dataclass(frozen=True)
class PublicUser:
    id: UUID
    username: str
    display_name: str | None
    bio: str | None
    ldap: bool
    role: UserRole
    is_active: bool
    last_seen_version: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    auth_provider: AuthProvider = AuthProvider.LOCAL
    oidc_subject: str | None = None
    oidc_email: str | None = None
    oidc_name: str | None = None
    oidc_groups: list[str] | None = None


class RegisterUser:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher

    def execute(self, command: RegisterUserCommand) -> PublicUser:
        existing_user = self.user_repository.get_by_username(command.username)

        if existing_user is not None:
            raise UsernameAlreadyExistsError

        user = UserCreate(
            username=command.username,
            display_name=None,
            bio=None,
            avatar_image=None,
            password_hash=self.password_hasher.hash_password(command.password),
            ldap=False,
            role=command.role,
        )

        try:
            created_user = self.user_repository.create(user)
        except UserPersistenceConflictError:
            raise UsernameAlreadyExistsError

        return user_to_public(created_user)


def user_to_public(user: User) -> PublicUser:
    return PublicUser(
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
