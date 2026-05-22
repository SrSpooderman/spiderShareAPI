from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.modules.auth.application.login import LoginUser
from app.modules.auth.application.password_hasher import PasswordHasher
from app.modules.auth.application.register import RegisterUser
from app.modules.auth.infrastructure.jwt_service import JwtService
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.user import User, UserRole, has_role_at_least
from app.modules.users.wiring import get_user_repository
from app.shared.infrastructure.logging import set_user_id


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_jwt_service() -> JwtService:
    return JwtService()


def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def get_register_user(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUser:
    return RegisterUser(user_repository, password_hasher)


def get_login_user(
    user_repository: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    jwt_service: JwtService = Depends(get_jwt_service),
) -> LoginUser:
    return LoginUser(user_repository, password_hasher, jwt_service)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    jwt_service: JwtService = Depends(get_jwt_service),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt_service.decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_error

    user = user_repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise credentials_error

    set_user_id(str(user.id))

    return user


def require_role_at_least(required_role: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_role_at_least(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        return current_user

    return dependency


require_admin = require_role_at_least(UserRole.ADMIN)
require_super_admin = require_role_at_least(UserRole.SUPER_ADMIN)
