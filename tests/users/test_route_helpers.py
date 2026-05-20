from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.users.entrypoints.routes import (
    _detect_image_media_type,
    _ensure_unique_username,
    _fields_set,
)
from app.modules.users.entrypoints.schemas import UserUpdateRequest


@pytest.mark.unit
@pytest.mark.parametrize(
    ("image", "expected_media_type"),
    [
        (b"\xff\xd8\xff\xe0jpeg-data", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\npng-data", "image/png"),
        (b"GIF87agif-data", "image/gif"),
        (b"GIF89agif-data", "image/gif"),
        (b"RIFFxxxxWEBPwebp-data", "image/webp"),
        (b"plain-bytes", "application/octet-stream"),
    ],
)
def test_detect_image_media_type(
    image: bytes,
    expected_media_type: str,
) -> None:
    assert _detect_image_media_type(image) == expected_media_type


@pytest.mark.unit
def test_fields_set_returns_only_sent_fields() -> None:
    request = UserUpdateRequest(display_name=None, bio="new bio")

    assert _fields_set(request) == {"display_name", "bio"}


@pytest.mark.unit
def test_ensure_unique_username_allows_current_users_username(
    user_factory,
    user_repository,
) -> None:
    target_user = user_factory(username="alice")
    user_repository.add(target_user)

    _ensure_unique_username("alice", target_user, user_repository)


@pytest.mark.unit
def test_ensure_unique_username_allows_available_username(
    user_factory,
    user_repository,
) -> None:
    target_user = user_factory(username="alice")
    user_repository.add(target_user)

    _ensure_unique_username("bob", target_user, user_repository)


@pytest.mark.unit
def test_ensure_unique_username_raises_conflict_for_another_user(
    user_factory,
    user_repository,
) -> None:
    target_user = user_factory(id=uuid4(), username="alice")
    existing_user = user_factory(id=uuid4(), username="bob")
    user_repository.add(target_user)
    user_repository.add(existing_user)

    with pytest.raises(HTTPException) as exc_info:
        _ensure_unique_username("bob", target_user, user_repository)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Username already exists"
