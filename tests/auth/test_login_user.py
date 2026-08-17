import pytest

from app.modules.auth.application.login import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginUser,
    LoginUserCommand,
)
from app.modules.users.domain.user import AuthProvider


@pytest.mark.unit
def test_login_user_returns_token_for_valid_credentials(
    user_factory,
    user_repository,
    password_hasher,
    access_token_service,
) -> None:
    user = user_factory(username="alice", password_hash="hashed:secret")
    user_repository.add(user)
    login_user = LoginUser(user_repository, password_hasher, access_token_service)

    result = login_user.execute(LoginUserCommand(username="alice", password="secret"))

    assert result.access_token == "fake-access-token"
    assert result.token_type == "bearer"
    assert result.user.username == "alice"
    assert access_token_service.users == [user]
    assert password_hasher.verified_passwords == [("secret", "hashed:secret")]
    assert user.last_login_at is not None
    assert user_repository.updated[0][1]["last_login_at"] == user.last_login_at


@pytest.mark.unit
def test_login_user_raises_invalid_credentials_when_username_does_not_exist(
    user_repository,
    password_hasher,
    access_token_service,
) -> None:
    login_user = LoginUser(user_repository, password_hasher, access_token_service)

    with pytest.raises(InvalidCredentialsError):
        login_user.execute(LoginUserCommand(username="missing", password="secret"))

    assert password_hasher.verified_passwords == []
    assert access_token_service.users == []


@pytest.mark.unit
def test_login_user_raises_invalid_credentials_when_password_is_wrong(
    user_factory,
    user_repository,
    password_hasher,
    access_token_service,
) -> None:
    user_repository.add(user_factory(username="alice", password_hash="hashed:secret"))
    login_user = LoginUser(user_repository, password_hasher, access_token_service)

    with pytest.raises(InvalidCredentialsError):
        login_user.execute(LoginUserCommand(username="alice", password="wrong"))

    assert password_hasher.verified_passwords == [("wrong", "hashed:secret")]
    assert access_token_service.users == []


@pytest.mark.unit
def test_login_user_rejects_oidc_users_even_with_matching_password(
    user_factory,
    user_repository,
    password_hasher,
    access_token_service,
) -> None:
    user_repository.add(
        user_factory(
            username="alice",
            password_hash="hashed:secret",
            auth_provider=AuthProvider.OIDC,
            oidc_subject="keycloak-user-id",
        )
    )
    login_user = LoginUser(user_repository, password_hasher, access_token_service)

    with pytest.raises(InvalidCredentialsError):
        login_user.execute(LoginUserCommand(username="alice", password="secret"))

    assert password_hasher.verified_passwords == []
    assert access_token_service.users == []


@pytest.mark.unit
def test_login_user_raises_inactive_user_when_user_is_not_active(
    user_factory,
    user_repository,
    password_hasher,
    access_token_service,
) -> None:
    user_repository.add(
        user_factory(
            username="alice",
            password_hash="hashed:secret",
            is_active=False,
        )
    )
    login_user = LoginUser(user_repository, password_hasher, access_token_service)

    with pytest.raises(InactiveUserError):
        login_user.execute(LoginUserCommand(username="alice", password="secret"))

    assert password_hasher.verified_passwords == [("secret", "hashed:secret")]
    assert access_token_service.users == []
