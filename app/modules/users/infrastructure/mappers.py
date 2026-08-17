import json
from uuid import UUID

from app.modules.users.domain.user import AuthProvider, User, UserCreate, UserRole
from app.modules.users.infrastructure.models import UserModel


def _decode_oidc_groups(value: str | None) -> list[str]:
    if not value:
        return []

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return []

    if not isinstance(decoded, list):
        return []

    return [str(group) for group in decoded if str(group).strip()]


def user_model_to_domain(model: UserModel) -> User:
    return User(
        id=UUID(model.id),
        username=model.username,
        display_name=model.display_name,
        bio=model.bio,
        avatar_image=model.avatar_image,
        password_hash=model.password_hash,
        ldap=model.ldap,
        auth_provider=AuthProvider(model.auth_provider or AuthProvider.LOCAL.value),
        oidc_subject=model.oidc_subject,
        oidc_email=model.oidc_email,
        oidc_name=model.oidc_name,
        oidc_groups=_decode_oidc_groups(model.oidc_groups),
        role=UserRole(model.role),
        is_active=model.is_active,
        last_seen_version=model.last_seen_version,
        last_login_at=model.last_login_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )

def user_create_to_model(user: UserCreate) -> UserModel:
    return UserModel(
        username=user.username,
        display_name=user.display_name,
        bio=user.bio,
        avatar_image=user.avatar_image,
        password_hash=user.password_hash,
        ldap=user.ldap,
        auth_provider=user.auth_provider.value,
        oidc_subject=user.oidc_subject,
        oidc_email=user.oidc_email,
        oidc_name=user.oidc_name,
        oidc_groups=json.dumps(user.oidc_groups or []),
        role=user.role.value,
    )

