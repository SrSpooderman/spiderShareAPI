import pytest

from app.modules.auth.application.register import (
    RegisterUser,
    RegisterUserCommand,
    UsernameAlreadyExistsError,
)
from app.modules.users.domain.user import UserRole


@pytest.mark.unit
def test_register_user_creates_user_when_username_is_available(
    user_repository,
    password_hasher,
) -> None:
    register_user = RegisterUser(user_repository, password_hasher)

    result = register_user.execute(
        RegisterUserCommand(username="alice", password="secret")
    )

    assert result.username == "alice"
    assert result.role == UserRole.USER
    assert result.is_active is True
    assert not hasattr(result, "password_hash")
    assert user_repository.created[0].password_hash == "hashed:secret"
    assert password_hasher.hashed_passwords == ["secret"]


@pytest.mark.unit
def test_register_user_uses_user_role_by_default(
    user_repository,
    password_hasher,
) -> None:
    register_user = RegisterUser(user_repository, password_hasher)

    result = register_user.execute(
        RegisterUserCommand(username="alice", password="secret")
    )

    assert result.role == UserRole.USER
    assert user_repository.created[0].role == UserRole.USER


@pytest.mark.unit
def test_register_user_respects_explicit_role(
    user_repository,
    password_hasher,
) -> None:
    register_user = RegisterUser(user_repository, password_hasher)

    result = register_user.execute(
        RegisterUserCommand(
            username="admin",
            password="secret",
            role=UserRole.ADMIN,
        )
    )

    assert result.role == UserRole.ADMIN
    assert user_repository.created[0].role == UserRole.ADMIN


@pytest.mark.unit
def test_register_user_raises_when_username_already_exists(
    user_factory,
    user_repository,
    password_hasher,
) -> None:
    user_repository.add(user_factory(username="alice"))
    register_user = RegisterUser(user_repository, password_hasher)

    with pytest.raises(UsernameAlreadyExistsError):
        register_user.execute(RegisterUserCommand(username="alice", password="secret"))

    assert user_repository.created == []
    assert password_hasher.hashed_passwords == []
