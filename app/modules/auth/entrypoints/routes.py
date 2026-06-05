import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app.modules.auth.application.login import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginUser,
    LoginUserCommand,
)
from app.modules.auth.application.register import (
    RegisterUser,
    RegisterUserCommand,
    UsernameAlreadyExistsError,
)
from app.modules.auth.entrypoints.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from app.modules.auth.wiring import (
    get_current_user,
    get_login_user,
    get_register_user,
    require_admin,
)
from app.modules.users.domain.user import User, can_create_user_with_role


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


async def _login_request_from_http_request(request: Request) -> LoginRequest:
    content_type = request.headers.get("content-type", "").lower()

    try:
        if content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data")):
            form = await request.form()
            return LoginRequest(
                username=str(form.get("username", "")),
                password=str(form.get("password", "")),
            )

        return LoginRequest.model_validate(await request.json())
    except ValidationError as error:
        detail = [
            {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    current_user: User = Depends(require_admin),
    register_user: RegisterUser = Depends(get_register_user),
) -> UserResponse:
    if not can_create_user_with_role(current_user.role, request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to create a user with that role",
        )

    try:
        user = register_user.execute(
            RegisterUserCommand(
                username=request.username,
                password=request.password,
                role=request.role,
            )
        )
    except UsernameAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    return UserResponse.from_public_user(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_user: LoginUser = Depends(get_login_user),
) -> LoginResponse:
    login_request = await _login_request_from_http_request(request)

    try:
        result = login_user.execute(
            LoginUserCommand(
                username=login_request.username,
                password=login_request.password,
            )
        )
    except InvalidCredentialsError:
        logger.warning("Login failed reason=invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserError:
        logger.warning("Login failed reason=inactive_user")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return LoginResponse.from_result(result)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_domain(current_user)
