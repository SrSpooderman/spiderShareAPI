import pytest

from app.modules.users.domain.user import (
    UserRole,
    can_create_user_with_role,
    can_manage_user,
    has_role_at_least,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("actual_role", "required_role", "expected"),
    [
        (UserRole.USER, UserRole.USER, True),
        (UserRole.USER, UserRole.ADMIN, False),
        (UserRole.USER, UserRole.SUPER_ADMIN, False),
        (UserRole.ADMIN, UserRole.USER, True),
        (UserRole.ADMIN, UserRole.ADMIN, True),
        (UserRole.ADMIN, UserRole.SUPER_ADMIN, False),
        (UserRole.SUPER_ADMIN, UserRole.USER, True),
        (UserRole.SUPER_ADMIN, UserRole.ADMIN, True),
        (UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN, True),
    ],
)
def test_has_role_at_least_compares_role_rank(
    actual_role: UserRole,
    required_role: UserRole,
    expected: bool,
) -> None:
    assert has_role_at_least(actual_role, required_role) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("creator_role", "target_role", "expected"),
    [
        (UserRole.SUPER_ADMIN, UserRole.USER, True),
        (UserRole.SUPER_ADMIN, UserRole.ADMIN, True),
        (UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN, False),
        (UserRole.ADMIN, UserRole.USER, True),
        (UserRole.ADMIN, UserRole.ADMIN, False),
        (UserRole.ADMIN, UserRole.SUPER_ADMIN, False),
        (UserRole.USER, UserRole.USER, False),
        (UserRole.USER, UserRole.ADMIN, False),
        (UserRole.USER, UserRole.SUPER_ADMIN, False),
    ],
)
def test_can_create_user_with_role_enforces_creation_rules(
    creator_role: UserRole,
    target_role: UserRole,
    expected: bool,
) -> None:
    assert can_create_user_with_role(creator_role, target_role) is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("manager_role", "target_role", "expected"),
    [
        (UserRole.SUPER_ADMIN, UserRole.ADMIN, True),
        (UserRole.SUPER_ADMIN, UserRole.USER, True),
        (UserRole.SUPER_ADMIN, UserRole.SUPER_ADMIN, False),
        (UserRole.ADMIN, UserRole.USER, True),
        (UserRole.ADMIN, UserRole.ADMIN, False),
        (UserRole.ADMIN, UserRole.SUPER_ADMIN, False),
        (UserRole.USER, UserRole.USER, False),
        (UserRole.USER, UserRole.ADMIN, False),
        (UserRole.USER, UserRole.SUPER_ADMIN, False),
    ],
)
def test_can_manage_user_requires_strictly_higher_role(
    manager_role: UserRole,
    target_role: UserRole,
    expected: bool,
) -> None:
    assert can_manage_user(manager_role, target_role) is expected
