from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from app.modules.auth.application.password_hasher import PasswordHasher
from app.modules.auth.application.register import PublicUser, user_to_public
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.user import User


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class AccessTokenService(Protocol):
    def create_access_token(self, user: User) -> str:
        pass


@dataclass(frozen=True)
class LoginUserCommand:
    username: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str
    user: PublicUser


class LoginUser:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        access_token_service: AccessTokenService,
    ) -> None:
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.access_token_service = access_token_service

    def execute(self, command: LoginUserCommand) -> LoginResult:
        user = self.user_repository.get_by_username(command.username)

        if user is None:
            raise InvalidCredentialsError

        if not self.password_hasher.verify_password(command.password, user.password_hash):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InactiveUserError

        updated_user = self.user_repository.update(
            user.id,
            last_login_at=datetime.now(timezone.utc),
        )
        if updated_user is not None:
            user = updated_user

        return LoginResult(
            access_token=self.access_token_service.create_access_token(user),
            token_type="bearer",
            user=user_to_public(user),
        )
