
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import ValidationError

from app.modules.auth.application.login import (
    InactiveUserError,
    InvalidCredentialsError,
    LoginUser,
    LoginUserCommand,
)
from app.modules.auth.application.oidc_login import (
    OidcAuthenticationError,
    OidcLogin,
    OidcLoginCommand,
)
from app.modules.auth.application.register import (
    RegisterUser,
    RegisterUserCommand,
    UsernameAlreadyExistsError,
)
from app.modules.auth.entrypoints.schemas import (
    LoginRequest,
    LoginResponse,
    OidcAuthorizeResponse,
    OidcCallbackRequest,
    RegisterRequest,
    UserResponse,
)
from app.modules.auth.wiring import (
    get_current_user,
    get_login_user,
    get_oidc_login,
    get_register_user,
    require_admin,
)
from app.modules.users.domain.user import User, can_create_user_with_role
from app.shared.infrastructure.logging import get_logger
from config.settings import settings


router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)
OIDC_STATE_AUDIENCE = "oidc-login"


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


def _ensure_oidc_enabled() -> None:
    if not settings.oidc_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC login is not enabled",
        )


def _safe_local_path(return_to: str | None) -> str:
    if not return_to:
        return "/dashboard"

    cleaned = return_to.strip()
    if not cleaned.startswith("/") or cleaned.startswith("//") or "://" in cleaned:
        return "/dashboard"

    return cleaned


def _normalized_domain(value: str) -> str:
    candidate = value.strip().lower().rstrip("/")
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    return parsed.netloc


def _allowed_frontend_domains() -> set[str]:
    return {
        normalized
        for domain in (settings.oidc_allowed_frontend_domains or settings.cors_allowed_origins)
        if (normalized := _normalized_domain(domain))
    }


def _frontend_state(return_to: str | None) -> dict[str, str]:
    parsed = urlparse(return_to or "")
    allowed_domains = _allowed_frontend_domains()

    if parsed.scheme in {"http", "https"} and parsed.netloc:
        domain = parsed.netloc.lower()
        if domain not in allowed_domains:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC return domain is not allowed",
            )

        origin = f"{parsed.scheme}://{parsed.netloc}"
        return {"frontend_origin": origin, "return_to": return_to or origin}

    return {
        "frontend_origin": "",
        "return_to": _safe_local_path(return_to),
    }


def _create_oidc_state(return_to: str | None = None) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    frontend_state = _frontend_state(return_to)
    return jwt.encode(
        {
            "aud": OIDC_STATE_AUDIENCE,
            "nonce": str(uuid4()),
            "exp": expires_at,
            **frontend_state,
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _validate_oidc_state(state: str) -> dict:
    try:
        return jwt.decode(
            state,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=OIDC_STATE_AUDIENCE,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OIDC state",
        )


def _oidc_redirect_uri() -> str:
    configured_redirect_uri = settings.oidc_redirect_uri
    if configured_redirect_uri and configured_redirect_uri.strip():
        return configured_redirect_uri

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="OIDC redirect URI is not configured",
    )


def _oidc_frontend_callback_uri(frontend_origin: str | None = None) -> str:
    if frontend_origin and frontend_origin.strip():
        callback_path = settings.oidc_frontend_callback_path
        if not callback_path.startswith("/"):
            callback_path = f"/{callback_path}"

        return f"{frontend_origin.rstrip('/')}{callback_path}"

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="OIDC frontend callback domain is not configured",
    )


def _redirect_with_query(base_url: str, params: dict[str, str]) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


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
        logger.warning(
            "Register failed reason=username_exists requested_username=%s created_by=%s",
            request.username,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    logger.info(
        "User registered user_id=%s username=%s role=%s created_by=%s",
        user.id,
        user.username,
        user.role.value,
        current_user.id,
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
        logger.warning(
            "Login failed reason=invalid_credentials username=%s",
            login_request.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserError:
        logger.warning(
            "Login failed reason=inactive_user username=%s",
            login_request.username,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    logger.info(
        "Login succeeded user_id=%s username=%s role=%s",
        result.user.id,
        result.user.username,
        result.user.role.value,
    )
    return LoginResponse.from_result(result)


@router.get("/oidc/authorize", response_model=OidcAuthorizeResponse)
def oidc_authorize(
    return_to: str | None = Query(default=None, min_length=1, max_length=2048),
    oidc_login: OidcLogin = Depends(get_oidc_login),
) -> OidcAuthorizeResponse:
    _ensure_oidc_enabled()
    state = _create_oidc_state(return_to)
    redirect_uri = _oidc_redirect_uri()
    state_payload = _validate_oidc_state(state)

    try:
        authorization_url = oidc_login.authorization_url(
            state=state,
            redirect_uri=redirect_uri,
        )
    except OidcAuthenticationError as error:
        logger.warning("OIDC authorize failed reason=%s", str(error))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC login is not available",
        )

    logger.info(
        "OIDC authorize created redirect_uri=%s frontend_origin=%s return_to=%s",
        redirect_uri,
        state_payload.get("frontend_origin"),
        state_payload.get("return_to"),
    )
    return OidcAuthorizeResponse(authorization_url=authorization_url, state=state)


@router.get("/oidc/callback", response_class=RedirectResponse)
def oidc_callback_redirect(
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=1),
    oidc_login: OidcLogin = Depends(get_oidc_login),
) -> RedirectResponse:
    _ensure_oidc_enabled()
    state_payload = _validate_oidc_state(state)
    redirect_uri = _oidc_redirect_uri()
    logger.info(
        "OIDC callback received redirect_uri=%s frontend_origin=%s return_to=%s",
        redirect_uri,
        state_payload.get("frontend_origin"),
        state_payload.get("return_to"),
    )

    try:
        result = oidc_login.execute(
            OidcLoginCommand(
                code=code,
                redirect_uri=redirect_uri,
            )
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    except OidcAuthenticationError as error:
        logger.warning("OIDC login failed reason=%s", str(error))
        return_to = str(state_payload.get("return_to"))
        redirect_url = _redirect_with_query(
            _oidc_frontend_callback_uri(str(state_payload.get("frontend_origin") or "")),
            {
                "error": "oidc_login_failed",
                "return_to": return_to,
            },
        )
        return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)

    return_to = str(state_payload.get("return_to") or "/dashboard")
    redirect_url = _redirect_with_query(
        _oidc_frontend_callback_uri(str(state_payload.get("frontend_origin") or "")),
        {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "return_to": return_to,
        },
    )
    return RedirectResponse(redirect_url, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/oidc/callback", response_model=LoginResponse)
def oidc_callback(
    request: OidcCallbackRequest,
    oidc_login: OidcLogin = Depends(get_oidc_login),
) -> LoginResponse:
    _ensure_oidc_enabled()
    _validate_oidc_state(request.state)

    try:
        result = oidc_login.execute(
            OidcLoginCommand(
                code=request.code,
                redirect_uri=_oidc_redirect_uri(),
            )
        )
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    except OidcAuthenticationError as error:
        logger.warning("OIDC login failed reason=%s", str(error))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OIDC login failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        "OIDC login succeeded user_id=%s username=%s role=%s",
        result.user.id,
        result.user.username,
        result.user.role.value,
    )
    return LoginResponse.from_result(result)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_domain(current_user)
