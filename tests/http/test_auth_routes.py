from dataclasses import dataclass

import pytest

from app.modules.auth.application.login import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginResult,
)
from app.modules.auth.application.register import (
    PublicUser,
    UsernameAlreadyExistsError,
)
from app.modules.auth.entrypoints.routes import get_current_user, get_login_user
from app.modules.auth.entrypoints.routes import get_register_user, require_admin
from app.modules.users.domain.user import UserRole


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
        json={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-123"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["user"]["username"] == "alice"
    assert login_user.command.username == "alice"
    assert login_user.command.password == "secret"


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
        json={"username": "alice", "password": "secret"},
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
        json={"username": "alice", "password": "secret", "role": "user"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "alice"
    assert register_user.command.username == "alice"
    assert register_user.command.password == "secret"
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
        json={"username": "boss", "password": "secret", "role": "admin"},
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
        json={"username": "alice", "password": "secret", "role": "user"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"
