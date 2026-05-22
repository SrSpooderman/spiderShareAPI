import pytest

from app.modules.auth.wiring import get_current_user, get_optional_current_user
from app.modules.videos.wiring import get_video_repository
from tests.factories import make_video_category, make_video_tag


@pytest.mark.http
def test_list_videos_supports_pagination_filters_and_popularity_order(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    category = make_video_category(name="Speedrun")
    tag = make_video_tag(name="boss")
    matching_high = video_repository.add(
        video_factory(
            owner_id=owner.id,
            title="Boss clip",
            favorite_count=8,
            categories=[category],
            tags=[tag],
        )
    )
    matching_low = video_repository.add(
        video_factory(
            owner_id=owner.id,
            title="Boss clip low",
            favorite_count=2,
            categories=[category],
            tags=[tag],
        )
    )
    video_repository.add(video_factory(title="Other clip", favorite_count=99))
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get(
        "/videos",
        params=[
            ("title", "boss"),
            ("tags", "boss"),
            ("category_ids", str(category.id)),
            ("owner_id", str(owner.id)),
            ("limit", "1"),
            ("offset", "0"),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert [item["id"] for item in body["items"]] == [str(matching_high.id)]

    response = client.get(
        "/videos",
        params=[
            ("title", "boss"),
            ("tags", "boss"),
            ("category_ids", str(category.id)),
            ("owner_id", str(owner.id)),
            ("limit", "1"),
            ("offset", "1"),
        ],
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(matching_low.id)]


@pytest.mark.http
def test_get_video_detail_includes_permissions_favorite_and_reactions(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    other_user = user_factory()
    video = video_repository.add(video_factory(owner_id=owner.id))
    video_repository.add_favorite(video.id, owner.id)
    video_repository.set_reaction(video.id, other_user.id, "like")
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_optional_current_user] = lambda: owner

    response = client.get(f"/videos/{video.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(video.id)
    assert body["is_owner"] is True
    assert body["can_edit"] is True
    assert body["can_delete"] is True
    assert body["is_favorite"] is True
    assert body["reactions"] == [{"type": "like", "count": 1}]


@pytest.mark.http
def test_patch_video_updates_metadata_and_sets_edited(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    video = video_repository.add(video_factory(owner_id=owner.id, edited=False))
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_current_user] = lambda: owner

    response = client.patch(
        f"/videos/{video.id}",
        json={"title": "New title", "is_registered_only": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New title"
    assert body["is_registered_only"] is True
    assert body["edited"] is True
    assert body["edited_at"] is not None


@pytest.mark.http
def test_delete_video_blocks_admin_but_allows_super_admin(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    admin = user_factory(role="admin")
    super_admin = user_factory(role="super_admin")
    admin_blocked_video = video_repository.add(video_factory(owner_id=owner.id))
    super_admin_video = video_repository.add(video_factory(owner_id=owner.id))
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.delete(f"/videos/{admin_blocked_video.id}")

    assert response.status_code == 403
    assert video_repository.get_by_id(admin_blocked_video.id) is not None

    app.dependency_overrides[get_current_user] = lambda: super_admin
    response = client.delete(f"/videos/{super_admin_video.id}")

    assert response.status_code == 204
    assert video_repository.get_by_id(super_admin_video.id) is None


@pytest.mark.http
def test_favorite_routes_and_my_favorites(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    user = user_factory()
    video = video_repository.add(video_factory())
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(f"/videos/{video.id}/favorite")

    assert response.status_code == 204
    assert video_repository.is_favorite(video.id, user.id) is True

    response = client.get("/users/me/video-favorites")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(video.id)

    response = client.delete(f"/videos/{video.id}/favorite")

    assert response.status_code == 204
    assert video_repository.is_favorite(video.id, user.id) is False


@pytest.mark.http
def test_reaction_routes_set_list_and_delete_reaction(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    user = user_factory()
    video = video_repository.add(video_factory())
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_current_user] = lambda: user

    response = client.post(
        f"/videos/{video.id}/reactions",
        json={"reaction_type": "like"},
    )

    assert response.status_code == 200
    assert response.json()["reaction_type"] == "like"

    response = client.get(f"/videos/{video.id}/reactions")

    assert response.status_code == 200
    assert response.json() == [{"type": "like", "count": 1}]

    response = client.delete(f"/videos/{video.id}/reactions")

    assert response.status_code == 204
    assert video_repository.get_reaction_counts(video.id) == {}
