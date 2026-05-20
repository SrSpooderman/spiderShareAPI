from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.modules.auth.application.password_hasher import PasswordHasher
from app.modules.auth.wiring import get_current_user, get_password_hasher, require_admin
from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.user import (
    User,
    UserRole,
    can_create_user_with_role,
    can_manage_user,
)
from app.modules.users.entrypoints.schemas import (
    PasswordChangeRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.modules.users.wiring import get_user_repository


router = APIRouter(prefix="/users", tags=["users"])

MAX_AVATAR_BYTES = 2 * 1024 * 1024


def _detect_image_media_type(image: bytes) -> str:
    if image.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image.startswith(b"GIF87a") or image.startswith(b"GIF89a"):
        return "image/gif"
    if image.startswith(b"RIFF") and image[8:12] == b"WEBP":
        return "image/webp"

    return "application/octet-stream"


def _fields_set(request: UserUpdateRequest) -> set[str]:
    fields_set = getattr(request, "model_fields_set", None)
    if fields_set is not None:
        return fields_set

    return getattr(request, "__fields_set__", set())


def _get_target_user(user_id: UUID, user_repository: UserRepository) -> User:
    user = user_repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def _ensure_can_access_target(current_user: User, target_user: User) -> bool:
    if current_user.id == target_user.id:
        return True

    if can_manage_user(current_user.role, target_user.role):
        return False

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not allowed to manage that user",
    )


def _ensure_unique_username(
    username: str,
    target_user: User,
    user_repository: UserRepository,
) -> None:
    existing_user = user_repository.get_by_username(username)
    if existing_user is not None and existing_user.id != target_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )


@router.get("", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(require_admin),
    user_repository: UserRepository = Depends(get_user_repository),
) -> list[UserResponse]:
    users = user_repository.list()
    visible_users = [
        user
        for user in users
        if user.id == current_user.id or can_manage_user(current_user.role, user.role)
    ]

    return [UserResponse.from_domain(user) for user in visible_users]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    target_user = _get_target_user(user_id, user_repository)
    _ensure_can_access_target(current_user, target_user)

    return UserResponse.from_domain(target_user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    target_user = _get_target_user(user_id, user_repository)
    is_self = _ensure_can_access_target(current_user, target_user)
    fields_set = _fields_set(request)

    if is_self and ({"role", "is_active"} & fields_set):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to change your own role or active status",
        )

    if "role" in fields_set:
        if request.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to assign super admin role",
            )
        if request.role is not None and not can_create_user_with_role(
            current_user.role,
            request.role,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to assign that role",
            )

    if request.username is not None:
        _ensure_unique_username(request.username, target_user, user_repository)

    updated_user = user_repository.update(
        user_id,
        username=request.username if "username" in fields_set else None,
        display_name=request.display_name if "display_name" in fields_set else None,
        bio=request.bio if "bio" in fields_set else None,
        role=request.role.value if request.role is not None else None,
        is_active=request.is_active if "is_active" in fields_set else None,
        clear_display_name="display_name" in fields_set and request.display_name is None,
        clear_bio="bio" in fields_set and request.bio is None,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.from_domain(updated_user)


@router.put("/{user_id}/avatar", response_model=UserResponse)
async def update_avatar(
    user_id: UUID,
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    target_user = _get_target_user(user_id, user_repository)
    _ensure_can_access_target(current_user, target_user)

    if avatar.content_type is None or not avatar.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be an image",
        )

    avatar_image = await avatar.read(MAX_AVATAR_BYTES + 1)
    if not avatar_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar image cannot be empty",
        )
    if len(avatar_image) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar image is too large",
        )

    updated_user = user_repository.update(user_id, avatar_image=avatar_image)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.from_domain(updated_user)


@router.delete("/{user_id}/avatar", response_model=UserResponse)
def delete_avatar(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    target_user = _get_target_user(user_id, user_repository)
    _ensure_can_access_target(current_user, target_user)

    updated_user = user_repository.update(user_id, clear_avatar_image=True)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.from_domain(updated_user)


@router.get("/{user_id}/avatar")
def get_avatar(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> Response:
    target_user = _get_target_user(user_id, user_repository)
    _ensure_can_access_target(current_user, target_user)

    if target_user.avatar_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found",
        )

    return Response(
        content=target_user.avatar_image,
        media_type=_detect_image_media_type(target_user.avatar_image),
    )


@router.patch("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    user_id: UUID,
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    user_repository: UserRepository = Depends(get_user_repository),
) -> Response:
    target_user = _get_target_user(user_id, user_repository)
    is_self = _ensure_can_access_target(current_user, target_user)

    if is_self:
        if request.current_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required",
            )
        if not password_hasher.verify_password(
            request.current_password,
            target_user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid current password",
            )

    user_repository.update(
        user_id,
        password_hash=password_hasher.hash_password(request.new_password),
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> Response:
    target_user = _get_target_user(user_id, user_repository)
    is_self = _ensure_can_access_target(current_user, target_user)

    if target_user.role == UserRole.SUPER_ADMIN and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete a super admin",
        )

    user_repository.delete(user_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
