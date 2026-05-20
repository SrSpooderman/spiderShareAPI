from uuid import uuid4

import pytest

from app.modules.users.domain.user import UserCreate, UserRole
from app.modules.users.infrastructure.mappers import (
    user_create_to_model,
    user_model_to_domain,
)
from app.modules.users.infrastructure.models import UserModel
from tests.factories import utc_now


@pytest.mark.unit
def test_user_create_to_model_preserves_user_fields() -> None:
    user_create = UserCreate(
        username="alice",
        display_name="Alice",
        bio="Bio",
        avatar_image=b"avatar",
        password_hash="hashed:secret",
        ldap=True,
        role=UserRole.ADMIN,
    )

    model = user_create_to_model(user_create)

    assert model.username == "alice"
    assert model.display_name == "Alice"
    assert model.bio == "Bio"
    assert model.avatar_image == b"avatar"
    assert model.password_hash == "hashed:secret"
    assert model.ldap is True
    assert model.role == "admin"


@pytest.mark.unit
def test_user_model_to_domain_converts_model_fields() -> None:
    user_id = uuid4()
    created_at = utc_now()
    updated_at = utc_now()
    last_login_at = utc_now()
    model = UserModel(
        id=str(user_id),
        username="alice",
        display_name="Alice",
        bio="Bio",
        avatar_image=b"avatar",
        password_hash="hashed:secret",
        ldap=False,
        role="super_admin",
        is_active=False,
        last_seen_version="1.2.3",
        last_login_at=last_login_at,
        created_at=created_at,
        updated_at=updated_at,
    )

    user = user_model_to_domain(model)

    assert user.id == user_id
    assert user.username == "alice"
    assert user.display_name == "Alice"
    assert user.bio == "Bio"
    assert user.avatar_image == b"avatar"
    assert user.password_hash == "hashed:secret"
    assert user.ldap is False
    assert user.role == UserRole.SUPER_ADMIN
    assert user.is_active is False
    assert user.last_seen_version == "1.2.3"
    assert user.last_login_at == last_login_at
    assert user.created_at == created_at
    assert user.updated_at == updated_at
