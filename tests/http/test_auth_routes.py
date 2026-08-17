from dataclasses import dataclass

import pytest

from app.modules.auth.application.login import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginResult,
)
from app.modules.auth.application.oidc_login import OidcAuthenticationError, OidcLoginCommand
from app.modules.auth.application.register import (
    PublicUser,
    UsernameAlreadyExistsError,
)
from app.modules.auth.entrypoints.routes import get_current_user, get_login_user
from app.modules.auth.entrypoints.routes import get_register_user, require_admin
from app.modules.auth.wiring import get_oidc_login
from app.modules.users.domain.user import UserRole
from config.settings import settings


@dataclass
class StubLoginUser:
    result: LoginResult | None = None
    error: Exception | None = None

    def execute(self, command):
        self.command = command
        if self.error is not None:
            raise self.error

        return self.result


@dataclass
class StubRegisterUser:
    result: PublicUser | None = None
    error: Exception | None = None

    def execute(self, command):
        self.command = command
        if self.error is not None:
            raise self.error

        return self.result


@dataclass
class StubOidcLogin:
    result: LoginResult | None = None
    error: Exception | None = None

    def authorization_url(self, *, state: str, redirect_uri: str) -> str:
        self.state = state
        self.redirect_uri = redirect_uri
        return f"https://keycloak.example/auth?state={state}"

    def execute(self, command: OidcLoginCommand) -> LoginResult:
        self.command = command
        if self.error is not None:
            raise self.error

        assert self.result is not None
        return self.result


@pytest.mark.http
def test_login_returns_token_for_valid_credentials(app, client, user_factory) -> None:
    user = user_factory(username="alice")
    login_user = StubLoginUser(
        result=LoginResult(
            access_token="token-123",
            token_type="bearer",
            user=PublicUser(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                ldap=user.ldap,
                role=user.role,
                is_active=user.is_active,
                last_seen_version=user.last_seen_version,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
    )
    app.dependency_overrides[get_login_user] = lambda: login_user

    response = client.post(
        "/auth/login",
        json={"username": "alice", "password": "supersecret"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-123"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["username"] == "alice"
    assert login_user.command.username == "alice"
    assert login_user.command.password == "supersecret"


@pytest.mark.http
def test_oidc_authorize_and_callback_return_internal_token(
    app,
    client,
    monkeypatch,
    user_factory,
) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://api.example.com/auth/oidc/callback")
    user = user_factory(username="alice")
    oidc_login = StubOidcLogin(
        result=LoginResult(
            access_token="oidc-token",
            token_type="bearer",
            user=PublicUser(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                ldap=True,
                role=user.role,
                is_active=user.is_active,
                last_seen_version=user.last_seen_version,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
    )
    app.dependency_overrides[get_oidc_login] = lambda: oidc_login

    authorize_response = client.get("/auth/oidc/authorize")

    assert authorize_response.status_code == 200
    state = authorize_response.json()["state"]
    assert authorize_response.json()["authorization_url"].startswith("https://keycloak.example/auth")

    callback_response = client.post(
        "/auth/oidc/callback",
        json={
            "code": "code-123",
            "state": state,
        },
    )

    assert callback_response.status_code == 200
    assert callback_response.json()["access_token"] == "oidc-token"
    assert oidc_login.command.code == "code-123"
    assert oidc_login.command.redirect_uri == "https://api.example.com/auth/oidc/callback"


@pytest.mark.http
def test_oidc_authorize_and_callback_strip_configured_redirect_uri(
    app,
    client,
    monkeypatch,
    user_factory,
) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(
        settings,
        "oidc_redirect_uri",
        " https://api.example.com/auth/oidc/callback ",
    )
    user = user_factory(username="alice")
    oidc_login = StubOidcLogin(
        result=LoginResult(
            access_token="oidc-token",
            token_type="bearer",
            user=PublicUser(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                ldap=True,
                role=user.role,
                is_active=user.is_active,
                last_seen_version=user.last_seen_version,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
    )
    app.dependency_overrides[get_oidc_login] = lambda: oidc_login

    authorize_response = client.get("/auth/oidc/authorize")
    state = authorize_response.json()["state"]
    assert oidc_login.redirect_uri == "https://api.example.com/auth/oidc/callback"

    client.post(
        "/auth/oidc/callback",
        json={"code": "code-123", "state": state},
    )

    assert oidc_login.command.redirect_uri == "https://api.example.com/auth/oidc/callback"


@pytest.mark.http
def test_oidc_authorize_and_get_callback_use_configured_redirect_uri(
    app,
    client,
    monkeypatch,
    user_factory,
) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://api.example.com/auth/oidc/callback")
    monkeypatch.setattr(
        settings,
        "oidc_allowed_frontend_domains",
        ["admin.example.com"],
    )
    monkeypatch.setattr(settings, "oidc_frontend_callback_path", "/login/oidc/callback")
    user = user_factory(username="alice")
    oidc_login = StubOidcLogin(
        result=LoginResult(
            access_token="oidc-token",
            token_type="bearer",
            user=PublicUser(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                ldap=True,
                role=user.role,
                is_active=user.is_active,
                last_seen_version=user.last_seen_version,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
    )
    app.dependency_overrides[get_oidc_login] = lambda: oidc_login

    authorize_response = client.get(
        "/auth/oidc/authorize",
        params={"return_to": "https://admin.example.com/videos"},
    )

    assert authorize_response.status_code == 200
    state = authorize_response.json()["state"]
    assert oidc_login.redirect_uri == "https://api.example.com/auth/oidc/callback"

    callback_response = client.get(
        "/auth/oidc/callback",
        params={"code": "code-123", "state": state},
        follow_redirects=False,
    )

    assert callback_response.status_code == 303
    assert callback_response.headers["location"].startswith(
        "https://admin.example.com/login/oidc/callback?"
    )
    assert "access_token=oidc-token" in callback_response.headers["location"]
    assert "return_to=https%3A%2F%2Fadmin.example.com%2Fvideos" in callback_response.headers["location"]
    assert oidc_login.command.code == "code-123"
    assert oidc_login.command.redirect_uri == "https://api.example.com/auth/oidc/callback"


@pytest.mark.http
def test_oidc_get_callback_redirects_to_frontend_with_error_when_login_fails(
    app,
    client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://api.example.com/auth/oidc/callback")
    monkeypatch.setattr(settings, "oidc_allowed_frontend_domains", ["admin.example.com"])
    monkeypatch.setattr(settings, "oidc_frontend_callback_path", "/login/oidc/callback")
    oidc_login = StubOidcLogin(error=OidcAuthenticationError("invalid code"))
    app.dependency_overrides[get_oidc_login] = lambda: oidc_login

    authorize_response = client.get(
        "/auth/oidc/authorize",
        params={"return_to": "https://admin.example.com/videos"},
    )
    state = authorize_response.json()["state"]

    callback_response = client.get(
        "/auth/oidc/callback",
        params={"code": "used-code", "state": state},
        follow_redirects=False,
    )

    assert callback_response.status_code == 303
    assert callback_response.headers["location"].startswith(
        "https://admin.example.com/login/oidc/callback?"
    )
    assert "error=oidc_login_failed" in callback_response.headers["location"]
    assert "return_to=https%3A%2F%2Fadmin.example.com%2Fvideos" in callback_response.headers["location"]
    assert oidc_login.command.redirect_uri == "https://api.example.com/auth/oidc/callback"


@pytest.mark.http
def test_oidc_authorize_rejects_unallowed_return_domain(
    app,
    client,
    monkeypatch,
    user_factory,
) -> None:
    monkeypatch.setattr(settings, "oidc_enabled", True)
    monkeypatch.setattr(settings, "oidc_redirect_uri", "https://api.example.com/auth/oidc/callback")
    monkeypatch.setattr(settings, "oidc_allowed_frontend_domains", ["admin.example.com"])
    app.dependency_overrides[get_oidc_login] = lambda: StubOidcLogin(
        result=LoginResult(
            access_token="oidc-token",
            token_type="bearer",
            user=PublicUser(
                id=user_factory().id,
                username="alice",
                display_name=None,
                bio=None,
                ldap=True,
                role=UserRole.USER,
                is_active=True,
                last_seen_version=None,
                last_login_at=None,
                created_at=user_factory().created_at,
                updated_at=user_factory().updated_at,
            ),
        )
    )

    response = client.get(
        "/auth/oidc/authorize",
        params={"return_to": "https://evil.example.com/videos"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "OIDC return domain is not allowed"


@pytest.mark.http
def test_login_accepts_swagger_oauth2_password_form(app, client, user_factory) -> None:
    user = user_factory(username="alice")
    login_user = StubLoginUser(
        result=LoginResult(
            access_token="token-123",
            token_type="bearer",
            user=PublicUser(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                bio=user.bio,
                ldap=user.ldap,
                role=user.role,
                is_active=user.is_active,
                last_seen_version=user.last_seen_version,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )
    )
    app.dependency_overrides[get_login_user] = lambda: login_user

    response = client.post(
        "/auth/login",
        data={
            "username": "alice",
            "password": "supersecret",
            "client_id": "",
            "client_secret": "",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-123"
    assert login_user.command.username == "alice"
    assert login_user.command.password == "supersecret"


@pytest.mark.http
def test_login_returns_401_for_invalid_credentials(app, client) -> None:
    app.dependency_overrides[get_login_user] = lambda: StubLoginUser(
        error=InvalidCredentialsError()
    )

    response = client.post(
        "/auth/login",
        json={"username": "alice", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.http
def test_login_returns_403_for_inactive_user(app, client) -> None:
    app.dependency_overrides[get_login_user] = lambda: StubLoginUser(
        error=InactiveUserError()
    )

    response = client.post(
        "/auth/login",
        json={"username": "alice", "password": "supersecret"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.http
def test_me_returns_current_user(app, client, user_factory) -> None:
    current_user = user_factory(username="alice")
    app.dependency_overrides[get_current_user] = lambda: current_user

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(current_user.id)
    assert response.json()["username"] == "alice"


@pytest.mark.http
def test_register_returns_created_user_for_allowed_role(
    app,
    client,
    user_factory,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    created = user_factory(username="alice")
    register_user = StubRegisterUser(
        result=PublicUser(
            id=created.id,
            username=created.username,
            display_name=created.display_name,
            bio=created.bio,
            ldap=created.ldap,
            role=created.role,
            is_active=created.is_active,
            last_seen_version=created.last_seen_version,
            last_login_at=created.last_login_at,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )
    )
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_register_user] = lambda: register_user

    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "supersecret", "role": "user"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert register_user.command.username == "alice"
    assert register_user.command.password == "supersecret"
    assert register_user.command.role == UserRole.USER


@pytest.mark.http
def test_register_returns_403_when_role_is_not_allowed(
    app,
    client,
    user_factory,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_register_user] = lambda: StubRegisterUser()

    response = client.post(
        "/auth/register",
        json={"username": "boss", "password": "supersecret", "role": "admin"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to create a user with that role"


@pytest.mark.http
def test_register_returns_409_when_username_exists(
    app,
    client,
    user_factory,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_register_user] = lambda: StubRegisterUser(
        error=UsernameAlreadyExistsError()
    )

    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "supersecret", "role": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.http
def test_register_rejects_blank_username(app, client, user_factory) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    app.dependency_overrides[require_admin] = lambda: admin
    register_user = StubRegisterUser()
    app.dependency_overrides[get_register_user] = lambda: register_user

    response = client.post(
        "/auth/register",
        json={"username": "   ", "password": "supersecret", "role": "user"},
    )

    assert response.status_code == 422
    assert not hasattr(register_user, "command")
