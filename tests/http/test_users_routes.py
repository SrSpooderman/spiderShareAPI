import pytest

from app.modules.auth.wiring import get_current_user, get_password_hasher, require_admin
from app.modules.users.domain.user import UserRole
from app.modules.users.wiring import get_user_repository


@pytest.mark.http
def test_list_users_returns_only_users_visible_to_admin(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    user = user_factory(username="alice", role=UserRole.USER)
    super_admin = user_factory(username="root", role=UserRole.SUPER_ADMIN)
    user_repository.add(admin)
    user_repository.add(user)
    user_repository.add(super_admin)
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.get("/users")

    assert response.status_code == 200
    assert {item["username"] for item in response.json()} == {"admin", "alice"}


@pytest.mark.http
def test_get_user_allows_current_user_to_read_self(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="alice")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.get(f"/users/{current_user.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(current_user.id)
    assert response.json()["username"] == "alice"


@pytest.mark.http
def test_get_user_returns_403_for_user_without_management_permission(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="alice", role=UserRole.USER)
    target_user = user_factory(username="bob", role=UserRole.USER)
    user_repository.add(current_user)
    user_repository.add(target_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.get(f"/users/{target_user.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to manage that user"


@pytest.mark.http
def test_patch_user_prevents_changing_own_role(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="admin", role=UserRole.ADMIN)
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.patch(
        f"/users/{current_user.id}",
        json={"role": "user"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not allowed to change your own role or active status"
    assert user_repository.updated == []


@pytest.mark.http
def test_patch_user_returns_409_when_username_exists(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    target_user = user_factory(username="alice", role=UserRole.USER)
    existing_user = user_factory(username="bob", role=UserRole.USER)
    user_repository.add(admin)
    user_repository.add(target_user)
    user_repository.add(existing_user)
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.patch(
        f"/users/{target_user.id}",
        json={"username": "bob"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"
    assert user_repository.updated == []


@pytest.mark.http
def test_patch_user_updates_profile_fields(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="alice")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.patch(
        f"/users/{current_user.id}",
        json={"display_name": "Alice", "bio": None},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Alice"
    assert response.json()["bio"] is None
    assert user_repository.updated[0][1]["clear_bio"] is True


@pytest.mark.http
def test_change_password_requires_current_password_for_self(
    app,
    client,
    user_factory,
    user_repository,
    password_hasher,
) -> None:
    current_user = user_factory(username="alice", password_hash="hashed:old")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_password_hasher] = lambda: password_hasher

    response = client.patch(
        f"/users/{current_user.id}/password",
        json={"new_password": "new"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is required"
    assert user_repository.updated == []


@pytest.mark.http
def test_change_password_updates_hash_with_valid_current_password(
    app,
    client,
    user_factory,
    user_repository,
    password_hasher,
) -> None:
    current_user = user_factory(username="alice", password_hash="hashed:old")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository
    app.dependency_overrides[get_password_hasher] = lambda: password_hasher

    response = client.patch(
        f"/users/{current_user.id}/password",
        json={"current_password": "old", "new_password": "new"},
    )

    assert response.status_code == 204
    assert current_user.password_hash == "hashed:new"
    assert password_hasher.verified_passwords == [("old", "hashed:old")]


@pytest.mark.http
def test_update_avatar_rejects_non_image_content(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="alice")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.put(
        f"/users/{current_user.id}/avatar",
        files={"avatar": ("avatar.txt", b"text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Avatar must be an image"


@pytest.mark.http
def test_update_and_get_avatar_round_trip_png(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    current_user = user_factory(username="alice")
    user_repository.add(current_user)
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    update_response = client.put(
        f"/users/{current_user.id}/avatar",
        files={"avatar": ("avatar.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
    )
    get_response = client.get(f"/users/{current_user.id}/avatar")

    assert update_response.status_code == 200
    assert update_response.json()["has_avatar"] is True
    assert get_response.status_code == 200
    assert get_response.content == b"\x89PNG\r\n\x1a\nimage"
    assert get_response.headers["content-type"] == "image/png"


@pytest.mark.http
def test_delete_user_returns_204_for_manageable_user(
    app,
    client,
    user_factory,
    user_repository,
) -> None:
    admin = user_factory(username="admin", role=UserRole.ADMIN)
    target_user = user_factory(username="alice", role=UserRole.USER)
    user_repository.add(admin)
    user_repository.add(target_user)
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_user_repository] = lambda: user_repository

    response = client.delete(f"/users/{target_user.id}")

    assert response.status_code == 204
    assert user_repository.get_by_id(target_user.id) is None
