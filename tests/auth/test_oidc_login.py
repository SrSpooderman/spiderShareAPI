from dataclasses import dataclass

import pytest

from app.modules.auth.application.oidc_login import OidcIdentity, OidcLogin, OidcLoginCommand
from app.modules.users.domain.user import AuthProvider
from tests.fakes import FakeAccessTokenService, FakeUserRepository


@dataclass
class StubOidcProvider:
    identity: OidcIdentity

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        return f"https://keycloak.example/auth?state={state}&redirect_uri={redirect_uri}"

    def authenticate(self, *, code: str, redirect_uri: str) -> OidcIdentity:
        self.code = code
        self.redirect_uri = redirect_uri
        return self.identity


@pytest.mark.unit
def test_oidc_login_creates_oidc_user_and_returns_internal_token() -> None:
    repository = FakeUserRepository()
    access_tokens = FakeAccessTokenService(token="clip-token")
    provider = StubOidcProvider(
        OidcIdentity(
            subject="keycloak-user-id",
            name="Alice Doe",
            email="alice@example.com",
            groups=["cliponomicon-admins"],
        )
    )
    login = OidcLogin(repository, access_tokens, provider)

    result = login.execute(
        OidcLoginCommand(
            code="auth-code",
            redirect_uri="http://localhost:5173/login/oidc/callback",
        )
    )

    assert result.access_token == "clip-token"
    assert result.user.auth_provider == AuthProvider.OIDC
    assert result.user.oidc_subject == "keycloak-user-id"
    assert result.user.oidc_email == "alice@example.com"
    assert result.user.oidc_groups == ["cliponomicon-admins"]
    assert repository.created[0].auth_provider == AuthProvider.OIDC
    assert repository.created[0].username == "alice"


@pytest.mark.unit
def test_oidc_login_does_not_link_existing_local_user_by_email(user_factory) -> None:
    local_user = user_factory(username="alice")
    repository = FakeUserRepository([local_user])
    access_tokens = FakeAccessTokenService()
    provider = StubOidcProvider(
        OidcIdentity(
            subject="keycloak-user-id",
            name="Alice Doe",
            email="alice@example.com",
            groups=[],
        )
    )
    login = OidcLogin(repository, access_tokens, provider)

    result = login.execute(
        OidcLoginCommand(
            code="auth-code",
            redirect_uri="http://localhost:5173/login/oidc/callback",
        )
    )

    assert result.user.id != local_user.id
    assert result.user.username.startswith("alice-keycloakuser")


@pytest.mark.unit
def test_oidc_login_reuses_local_user_linked_by_keycloak_subject(user_factory) -> None:
    oidc_user = user_factory(
        username="alice",
        auth_provider=AuthProvider.OIDC,
        oidc_subject="keycloak-user-id",
        oidc_email="old@example.com",
        oidc_name="Old Name",
        oidc_groups=["old-group"],
    )
    repository = FakeUserRepository([oidc_user])
    access_tokens = FakeAccessTokenService()
    provider = StubOidcProvider(
        OidcIdentity(
            subject="keycloak-user-id",
            name="Alice Doe",
            email="alice@example.com",
            groups=["cliponomicon-admins"],
        )
    )
    login = OidcLogin(repository, access_tokens, provider)

    result = login.execute(
        OidcLoginCommand(
            code="auth-code",
            redirect_uri="https://api.example.com/auth/oidc/callback",
        )
    )

    assert result.user.id == oidc_user.id
    assert result.user.auth_provider == AuthProvider.OIDC
    assert result.user.oidc_subject == "keycloak-user-id"
    assert result.user.oidc_email == "alice@example.com"
    assert result.user.oidc_name == "Alice Doe"
    assert result.user.oidc_groups == ["cliponomicon-admins"]
    assert repository.created == []
