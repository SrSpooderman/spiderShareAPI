import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.modules.auth.application.login import AccessTokenService, InactiveUserError, LoginResult
from app.modules.auth.application.register import user_to_public
from app.modules.users.domain.ports import UserPersistenceConflictError, UserRepository
from app.modules.users.domain.user import AuthProvider, User, UserCreate, UserRole


class OidcAuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class OidcIdentity:
    subject: str
    name: str | None
    email: str | None
    groups: list[str]


class OidcProvider(Protocol):
    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        pass

    def authenticate(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        pass


@dataclass(frozen=True)
class OidcLoginCommand:
    code: str
    redirect_uri: str


class OidcLogin:
    def __init__(
        self,
        user_repository: UserRepository,
        access_token_service: AccessTokenService,
        oidc_provider: OidcProvider,
        *,
        default_role: UserRole = UserRole.USER,
    ) -> None:
        self.user_repository = user_repository
        self.access_token_service = access_token_service
        self.oidc_provider = oidc_provider
        self.default_role = default_role

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        return self.oidc_provider.authorization_url(state=state, redirect_uri=redirect_uri)

    def execute(self, command: OidcLoginCommand) -> LoginResult:
        identity = self.oidc_provider.authenticate(
            code=command.code,
            redirect_uri=command.redirect_uri,
        )
        user = self.user_repository.get_by_oidc_subject(identity.subject)

        if user is None:
            user = self._create_user(identity)
        else:
            user = self._refresh_user_claims(user, identity)

        if not user.is_active:
            raise InactiveUserError

        updated_user = self.user_repository.update(
            user.id,
            oidc_email=identity.email,
            oidc_name=identity.name,
            oidc_groups=identity.groups,
            last_login_at=datetime.now(timezone.utc),
        )
        if updated_user is not None:
            user = updated_user

        return LoginResult(
            access_token=self.access_token_service.create_access_token(user),
            refresh_token=self.access_token_service.create_refresh_token(user),
            token_type="bearer",
            user=user_to_public(user),
        )

    def _create_user(self, identity: OidcIdentity) -> User:
        username = self._unique_username(identity)
        user = UserCreate(
            username=username,
            display_name=identity.name,
            bio=None,
            avatar_image=None,
            password_hash="!oidc",
            ldap=True,
            auth_provider=AuthProvider.OIDC,
            oidc_subject=identity.subject,
            oidc_email=identity.email,
            oidc_name=identity.name,
            oidc_groups=identity.groups,
            role=self.default_role,
        )

        try:
            return self.user_repository.create(user)
        except UserPersistenceConflictError as error:
            raise OidcAuthenticationError("OIDC user could not be created") from error

    def _refresh_user_claims(self, user: User, identity: OidcIdentity) -> User:
        updated_user = self.user_repository.update(
            user.id,
            display_name=identity.name,
            oidc_email=identity.email,
            oidc_name=identity.name,
            oidc_groups=identity.groups,
        )
        return updated_user or user

    def _unique_username(self, identity: OidcIdentity) -> str:
        base = _candidate_username(identity)
        candidate = base
        suffix = _short_subject(identity.subject)
        counter = 1

        while self.user_repository.get_by_username(candidate) is not None:
            candidate = f"{base}-{suffix}" if counter == 1 else f"{base}-{suffix}-{counter}"
            counter += 1

        return candidate


def _candidate_username(identity: OidcIdentity) -> str:
    raw = identity.email or identity.name or identity.subject
    local_part = raw.split("@", maxsplit=1)[0]
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", local_part).strip("-_.").lower()
    return normalized[:100] or _short_subject(identity.subject)


def _short_subject(subject: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", subject).lower()
    return (normalized or "oidc")[:12]
