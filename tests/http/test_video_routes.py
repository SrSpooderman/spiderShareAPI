import pytest
from uuid import uuid4

from app.modules.auth.wiring import get_current_user, get_optional_current_user
from app.modules.videos.wiring import (
    get_video_category_repository,
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
    get_video_tag_repository,
)
from app.modules.steam.wiring import get_steamgriddb_client
from app.modules.videos.domain.video import VideoProcessingStatus, VideoVariantType
from tests.factories import make_video_category, make_video_tag, make_video_variant
from tests.fakes import FakeSteamGridDbClient


@pytest.mark.http
def test_list_videos_supports_pagination_filters_and_popularity_order(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory(username="owner", display_name="Owner")
    category = make_video_category(name="Speedrun")
    tag = make_video_tag(name="boss")
    matching_high = video_repository.add(
        video_factory(
            owner_id=owner.id,
            owner_username=owner.username,
            owner_display_name=owner.display_name,
            title="Boss clip",
            favorite_count=8,
            categories=[category],
            tags=[tag],
        )
    )
    matching_low = video_repository.add(
        video_factory(
            owner_id=owner.id,
            owner_username=owner.username,
            owner_display_name=owner.display_name,
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
            ("tag_ids", str(tag.id)),
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
    assert body["items"][0]["popularity_score"] == matching_high.favorite_count * 4
    assert body["items"][0]["owner"] == {
        "id": str(owner.id),
        "username": "owner",
        "display_name": "Owner",
    }
    assert body["items"][0]["original_filename"] == matching_high.original_filename
    assert body["items"][0]["clip_url"] == f"/clip/{matching_high.id}"
    assert body["items"][0]["download_url"] == f"/videos/{matching_high.id}/download"
    assert body["items"][0]["is_owner"] is False
    assert body["items"][0]["can_edit"] is False
    assert body["items"][0]["can_delete"] is False
    assert body["items"][0]["is_favorite"] is False
    assert body["items"][0]["reactions"] == []

    response = client.get(
        "/videos",
        params=[
            ("title", "boss"),
            ("tag_ids", str(tag.id)),
            ("category_ids", str(category.id)),
            ("owner_id", str(owner.id)),
            ("limit", "1"),
            ("offset", "1"),
        ],
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [str(matching_low.id)]
    assert response.json()["items"][0]["popularity_score"] == matching_low.favorite_count * 4


@pytest.mark.http
def test_upload_video_creates_video_and_stores_original(
    app,
    client,
    user_factory,
    video_repository,
    video_storage,
    video_transcoder,
    video_processing_queue,
) -> None:
    user = user_factory(username="alice", display_name="Alice")
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(
        "/videos",
        data={
            "title": "Boss clip",
            "description": "Context",
            "edited": "true",
            "tag_ids": [str(make_video_tag().id), str(make_video_tag().id)],
        },
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Boss clip"
    assert "owner_id" not in body
    assert body["owner"] == {
        "id": str(user.id),
        "username": "alice",
        "display_name": "Alice",
    }
    assert body["original_filename"] == "clip.mp4"
    assert body["processing_status"] == "pending"
    assert body["edited"] is True
    assert body["edited_at"] is None
    assert body["width"] is None
    assert body["height"] is None
    assert body["duration_seconds"] is None
    assert body["thumbnail_path"] is None
    assert body["playback_url"] is None
    assert body["clip_url"] == f"/clip/{body['id']}"
    assert body["download_url"] == f"/videos/{body['id']}/download"
    assert body["thumbnail_url"] is None
    assert body["variants"] == []
    assert video_repository.created[0].id == video_storage.saved[0]["video_id"]
    assert video_storage.saved[0]["content"] == b"video-bytes"
    assert video_processing_queue.enqueued == [video_repository.created[0].id]
    assert video_transcoder.transcoded == []


@pytest.mark.http
def test_upload_video_allows_missing_description(
    app,
    client,
    user_factory,
    video_repository,
    video_storage,
    video_transcoder,
    video_processing_queue,
) -> None:
    user = user_factory()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(
        "/videos",
        data={"title": "Boss clip"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 201
    assert response.json()["description"] == ""
    assert video_processing_queue.enqueued == [video_repository.created[0].id]


@pytest.mark.http
def test_list_and_create_custom_video_categories(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    video_category_repository.add(make_video_category(name="Existing"))
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.get("/category")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Existing"
    assert response.json()[0]["source"] == "custom"

    response = client.post(
        "/category",
        json={
            "name": "Indie",
            "thumbnail_vertical_url": "https://cdn.example.com/indie-v.jpg",
            "thumbnail_horizontal_url": "https://cdn.example.com/indie-h.jpg",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Indie"
    assert body["source"] == "custom"
    assert body["steam_appid"] is None
    assert body["thumbnail_vertical_url"] == "https://cdn.example.com/indie-v.jpg"
    assert video_category_repository.created[0].name == "Indie"


@pytest.mark.http
def test_list_and_create_video_tags(
    app,
    client,
    user_factory,
    video_tag_repository,
) -> None:
    user = user_factory()
    video_tag_repository.add(make_video_tag(name="Existing"))
    app.dependency_overrides[get_video_tag_repository] = lambda: video_tag_repository
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.get("/tags")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Existing"

    response = client.post("/tags", json={"name": "Boss"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Boss"
    assert video_tag_repository.created[0].name == "Boss"


@pytest.mark.http
def test_update_video_tag(
    app,
    client,
    user_factory,
    video_tag_repository,
) -> None:
    user = user_factory()
    tag = video_tag_repository.add(make_video_tag(name="Old name"))
    app.dependency_overrides[get_video_tag_repository] = lambda: video_tag_repository
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.patch(f"/tags/{tag.id}", json={"name": "New name"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(tag.id)
    assert body["name"] == "New name"

    response = client.patch(f"/tags/{uuid4()}", json={"name": "Missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Video tag not found"


@pytest.mark.http
def test_delete_video_tag_requires_admin(
    app,
    client,
    user_factory,
    video_tag_repository,
) -> None:
    user = user_factory()
    admin = user_factory(role="admin")
    tag = video_tag_repository.add(make_video_tag(name="To delete"))
    app.dependency_overrides[get_video_tag_repository] = lambda: video_tag_repository
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.delete(f"/tags/{tag.id}")

    assert response.status_code == 403
    assert tag.id in video_tag_repository.tags

    app.dependency_overrides[get_current_user] = lambda: admin
    response = client.delete(f"/tags/{tag.id}")

    assert response.status_code == 204
    assert tag.id not in video_tag_repository.tags

    response = client.delete(f"/tags/{tag.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video tag not found"


@pytest.mark.http
def test_update_video_category(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    category = video_category_repository.add(
        make_video_category(
            name="Old name",
            thumbnail_vertical_url="https://cdn.example.com/old-v.jpg",
            thumbnail_horizontal_url="https://cdn.example.com/old-h.jpg",
        )
    )
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.patch(
        f"/category/{category.id}",
        json={
            "name": "New name",
            "thumbnail_vertical_url": "https://cdn.example.com/new-v.jpg",
            "thumbnail_horizontal_url": "https://cdn.example.com/new-h.jpg",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(category.id)
    assert body["name"] == "New name"
    assert body["source"] == "custom"
    assert body["thumbnail_vertical_url"] == "https://cdn.example.com/new-v.jpg"
    assert body["thumbnail_horizontal_url"] == "https://cdn.example.com/new-h.jpg"

    response = client.patch(
        f"/category/{uuid4()}",
        json={"name": "Missing"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Video category not found"


@pytest.mark.http
def test_delete_video_category(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    category = video_category_repository.add(make_video_category(name="To delete"))
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.delete(f"/category/{category.id}")

    assert response.status_code == 204
    assert video_category_repository.get_by_id(category.id) is None

    response = client.delete(f"/category/{category.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Video category not found"


@pytest.mark.http
def test_search_steamgriddb_games_for_video_categories(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    steamgriddb_client = FakeSteamGridDbClient(
        games_by_search={
            "portal": [
                {
                    "id": 22,
                    "name": "Portal",
                    "types": ["game"],
                    "verified": True,
                },
                {"id": None, "name": "Broken"},
            ]
        }
    )
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_steamgriddb_client] = lambda: steamgriddb_client
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.get("/category/steam/search?term=portal")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 22, "name": "Portal", "types": ["game"], "verified": True}
    ]
    assert steamgriddb_client.search_requests == ["portal"]


@pytest.mark.http
def test_list_steamgriddb_grids_for_video_category_selection(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    steamgriddb_client = FakeSteamGridDbClient(
        grids_by_game_dimensions={
            (22, "600x900"): [
                {
                    "id": 1,
                    "url": "https://cdn.example.com/portal-v-1.jpg",
                    "thumb": "https://cdn.example.com/portal-v-1-thumb.jpg",
                    "width": 600,
                    "height": 900,
                    "style": "alternate",
                    "nsfw": False,
                    "humor": False,
                    "epilepsy": False,
                },
                {
                    "id": 2,
                    "url": "https://cdn.example.com/portal-v-2.jpg",
                    "width": 600,
                    "height": 900,
                },
                {
                    "id": 3,
                    "url": "https://cdn.example.com/portal-v-3.jpg",
                    "width": 600,
                    "height": 900,
                },
            ],
        },
    )
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_steamgriddb_client] = lambda: steamgriddb_client
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.get(
        "/category/steam/games/22/grids",
        params={"dimensions": "600x900", "limit": 2, "offset": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["has_more"] is True
    assert body["next_offset"] == 2
    assert [item["url"] for item in body["items"]] == [
        "https://cdn.example.com/portal-v-1.jpg",
        "https://cdn.example.com/portal-v-2.jpg",
    ]
    assert body["items"][0]["thumb"] == "https://cdn.example.com/portal-v-1-thumb.jpg"
    assert steamgriddb_client.grid_requests == [(22, "600x900", 3, 1)]


@pytest.mark.http
def test_import_steam_video_category_uses_stable_grid_dimensions(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    steamgriddb_client = FakeSteamGridDbClient(
        games_by_appid={400: {"id": 22, "name": "Portal"}},
        grids_by_game_dimensions={
            (22, "600x900"): [{"url": "https://cdn.example.com/portal-v.jpg"}],
            (22, "920x430"): [{"url": "https://cdn.example.com/portal-h.jpg"}],
        },
    )
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_steamgriddb_client] = lambda: steamgriddb_client
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.post(
        "/category/steam/import",
        json={"steam_appid": 400},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Portal"
    assert body["source"] == "steam"
    assert body["steam_appid"] == 400
    assert body["steamgriddb_game_id"] == 22
    assert body["thumbnail_vertical_url"] == "https://cdn.example.com/portal-v.jpg"
    assert body["thumbnail_horizontal_url"] == "https://cdn.example.com/portal-h.jpg"
    assert steamgriddb_client.grid_requests == [
        (22, "600x900", 1, None),
        (22, "920x430", 1, None),
    ]
    assert video_category_repository.upserted[0].steam_appid == 400


@pytest.mark.http
def test_import_steam_video_category_uses_selected_grid_urls(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    steamgriddb_client = FakeSteamGridDbClient(
        games_by_appid={400: {"id": 22, "name": "Portal"}},
    )
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_steamgriddb_client] = lambda: steamgriddb_client
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.post(
        "/category/steam/import",
        json={
            "steam_appid": 400,
            "thumbnail_vertical_url": "https://cdn.example.com/selected-v.jpg",
            "thumbnail_horizontal_url": "https://cdn.example.com/selected-h.jpg",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["thumbnail_vertical_url"] == "https://cdn.example.com/selected-v.jpg"
    assert body["thumbnail_horizontal_url"] == "https://cdn.example.com/selected-h.jpg"
    assert steamgriddb_client.grid_requests == []
    assert video_category_repository.upserted[0].thumbnail_vertical_url == (
        "https://cdn.example.com/selected-v.jpg"
    )


@pytest.mark.http
def test_import_steam_video_category_requires_external_id(
    app,
    client,
    user_factory,
    video_category_repository,
) -> None:
    admin = user_factory(role="admin")
    app.dependency_overrides[get_video_category_repository] = (
        lambda: video_category_repository
    )
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.post("/category/steam/import", json={})

    assert response.status_code == 422
    assert video_category_repository.upserted == []


@pytest.mark.http
def test_upload_video_replays_response_for_same_idempotency_key(
    app,
    client,
    user_factory,
    video_repository,
    video_storage,
    video_processing_queue,
) -> None:
    user = user_factory()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user

    first_response = client.post(
        "/videos",
        headers={"Idempotency-Key": "upload-1"},
        data={"title": "Boss clip", "description": "Context"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )
    second_response = client.post(
        "/videos",
        headers={"Idempotency-Key": "upload-1"},
        data={"title": "Boss clip", "description": "Context"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert second_response.json() == first_response.json()
    assert len(video_repository.created) == 1
    assert len(video_storage.saved) == 1
    assert video_processing_queue.enqueued == [video_repository.created[0].id]


@pytest.mark.http
def test_upload_video_rejects_reused_idempotency_key_with_different_request(
    app,
    client,
    user_factory,
    video_repository,
    video_storage,
) -> None:
    user = user_factory()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user

    first_response = client.post(
        "/videos",
        headers={"Idempotency-Key": "upload-1"},
        data={"title": "Boss clip"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )
    second_response = client.post(
        "/videos",
        headers={"Idempotency-Key": "upload-1"},
        data={"title": "Different title"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Idempotency-Key was already used with a different request"
    )
    assert len(video_repository.created) == 1
    assert len(video_storage.saved) == 1


@pytest.mark.http
def test_upload_video_rolls_back_when_processing_queue_is_unavailable(
    app,
    client,
    user_factory,
    video_repository,
    video_storage,
) -> None:
    from tests.fakes import FakeVideoProcessingQueue

    user = user_factory()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_video_processing_queue] = lambda: FakeVideoProcessingQueue(
        RuntimeError("redis unavailable")
    )

    response = client.post(
        "/videos",
        data={"title": "Boss clip"},
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Video processing queue is unavailable"
    assert video_repository.created[0].id in video_repository.deleted
    assert video_storage.deleted_all == [video_repository.created[0].id]


@pytest.mark.http
def test_get_video_detail_includes_permissions_favorite_and_reactions(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory(username="owner", display_name="Owner")
    other_user = user_factory()
    video = video_repository.add(
        video_factory(
            owner_id=owner.id,
            owner_username=owner.username,
            owner_display_name=owner.display_name,
        )
    )
    video_repository.add_favorite(video.id, owner.id)
    video_repository.set_reaction(video.id, other_user.id, "like")
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_optional_current_user] = lambda: owner

    response = client.get(f"/videos/{video.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(video.id)
    assert body["owner"] == {
        "id": str(owner.id),
        "username": "owner",
        "display_name": "Owner",
    }
    assert body["is_owner"] is True
    assert body["can_edit"] is True
    assert body["can_delete"] is True
    assert body["is_favorite"] is True
    assert body["reactions"] == [{"type": "like", "count": 1}]


@pytest.mark.http
def test_video_download_stream_and_thumbnail_respect_visibility(
    app,
    client,
    tmp_path,
    user_factory,
    video_factory,
    video_repository,
    video_storage,
) -> None:
    owner = user_factory()
    video = video_repository.add(
        video_factory(
            owner_id=owner.id,
            processing_status=VideoProcessingStatus.READY,
            thumbnail_path=f"thumbnails/video/{owner.id}.jpg",
            variants=[
                make_video_variant(
                    video_id=owner.id,
                    path="variants/video/low_h264.mp4",
                ),
                make_video_variant(
                    video_id=owner.id,
                    variant_type=VideoVariantType.ORIGINAL_H264,
                    path="variants/video/original_h264.mp4",
                ),
            ],
        )
    )
    original_path = tmp_path / "original.mp4"
    original_h264_path = tmp_path / "original_h264.mp4"
    stream_path = tmp_path / "low_h264.mp4"
    thumbnail_path = tmp_path / "thumbnail.jpg"
    original_path.write_bytes(b"original-video")
    original_h264_path.write_bytes(b"original-h264-video")
    stream_path.write_bytes(b"stream-video")
    thumbnail_path.write_bytes(b"thumbnail")
    video_storage.original_paths[video.id] = original_path
    video_storage.variant_paths[(video.id, "original_h264")] = original_h264_path
    video_storage.variant_paths[(video.id, "low_h264")] = stream_path
    video_storage.thumbnail_paths[video.id] = thumbnail_path
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get(f"/videos/{video.id}/download")

    assert response.status_code == 200
    assert response.content == b"original-video"
    assert response.headers["content-disposition"].startswith("attachment;")

    response = client.get(f"/videos/{video.id}/stream")

    assert response.status_code == 200
    assert response.content == b"stream-video"
    assert response.headers["content-type"].startswith("video/mp4")

    response = client.get(f"/clip/{video.id}")

    assert response.status_code == 200
    assert response.content == b"original-h264-video"
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.headers["content-disposition"].startswith("inline;")

    response = client.get(f"/clip/{video.id}/h264")

    assert response.status_code == 200
    assert response.content == b"original-h264-video"
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.headers["content-disposition"].startswith("inline;")

    response = client.get(f"/videos/{video.id}/stream?variant_type=original")

    assert response.status_code == 200
    assert response.content == b"original-video"
    assert response.headers["content-type"].startswith("video/mp4")
    assert response.headers["content-disposition"].startswith("inline;")

    response = client.get(f"/videos/{video.id}/thumbnail")

    assert response.status_code == 200
    assert response.content == b"thumbnail"
    assert response.headers["content-type"].startswith("image/jpeg")


@pytest.mark.http
def test_original_stream_works_for_pending_video(
    app,
    client,
    tmp_path,
    video_factory,
    video_repository,
    video_storage,
) -> None:
    video = video_repository.add(
        video_factory(processing_status=VideoProcessingStatus.PENDING)
    )
    original_path = tmp_path / "original.webm"
    original_path.write_bytes(b"original-video")
    video_storage.original_paths[video.id] = original_path
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get(f"/videos/{video.id}/stream?variant_type=original")

    assert response.status_code == 200
    assert response.content == b"original-video"
    assert response.headers["content-type"].startswith("video/webm")


@pytest.mark.http
def test_registered_only_video_files_require_login(
    app,
    client,
    tmp_path,
    user_factory,
    video_factory,
    video_repository,
    video_storage,
) -> None:
    user = user_factory()
    video = video_repository.add(
        video_factory(
            is_registered_only=True,
            processing_status=VideoProcessingStatus.READY,
            variants=[make_video_variant()],
        )
    )
    original_path = tmp_path / "original.mp4"
    original_path.write_bytes(b"original-video")
    video_storage.original_paths[video.id] = original_path
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get(f"/videos/{video.id}/download")

    assert response.status_code == 403

    response = client.get(f"/clip/{video.id}")

    assert response.status_code == 403

    app.dependency_overrides[get_optional_current_user] = lambda: user
    response = client.get(f"/videos/{video.id}/download")

    assert response.status_code == 200


@pytest.mark.http
def test_clip_link_requires_ready_video(
    app,
    client,
    tmp_path,
    video_factory,
    video_repository,
    video_storage,
) -> None:
    video = video_repository.add(
        video_factory(processing_status=VideoProcessingStatus.PENDING)
    )
    original_path = tmp_path / "original.mp4"
    original_path.write_bytes(b"original-video")
    video_storage.original_paths[video.id] = original_path
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_optional_current_user] = lambda: None

    response = client.get(f"/clip/{video.id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Video is not ready"


@pytest.mark.http
def test_patch_video_updates_metadata_and_only_sets_edited_when_requested(
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
    assert body["edited"] is False
    assert body["edited_at"] is None

    response = client.patch(
        f"/videos/{video.id}",
        json={"edited": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["edited"] is True
    assert body["edited_at"] is None


@pytest.mark.http
def test_patch_video_replaces_tags_independently_from_categories(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
) -> None:
    owner = user_factory()
    category = make_video_category(name="Speedrun")
    boss_tag = video_repository.add_tag(make_video_tag(name="boss"))
    clip_tag = video_repository.add_tag(make_video_tag(name="clip"))
    video = video_repository.add(
        video_factory(
            owner_id=owner.id,
            categories=[category],
            tags=[make_video_tag(name="old")],
        )
    )
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_current_user] = lambda: owner

    response = client.patch(
        f"/videos/{video.id}",
        json={"tag_ids": [str(boss_tag.id), str(clip_tag.id), str(boss_tag.id)]},
    )

    assert response.status_code == 200
    body = response.json()
    assert [tag["name"] for tag in body["tags"]] == ["boss", "clip"]
    assert [category["id"] for category in body["categories"]] == [str(category.id)]
    assert video_repository.updated[-1][1]["tag_ids"] == [
        boss_tag.id,
        clip_tag.id,
    ]
    assert video_repository.updated[-1][1]["category_ids"] is None


@pytest.mark.http
def test_delete_video_blocks_admin_but_allows_super_admin(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
    video_storage,
) -> None:
    owner = user_factory()
    admin = user_factory(role="admin")
    super_admin = user_factory(role="super_admin")
    admin_blocked_video = video_repository.add(video_factory(owner_id=owner.id))
    super_admin_video = video_repository.add(video_factory(owner_id=owner.id))
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.delete(f"/videos/{admin_blocked_video.id}")

    assert response.status_code == 403
    assert video_repository.get_by_id(admin_blocked_video.id) is not None

    app.dependency_overrides[get_current_user] = lambda: super_admin
    response = client.delete(f"/videos/{super_admin_video.id}")

    assert response.status_code == 204
    assert video_repository.get_by_id(super_admin_video.id) is None
    assert video_storage.deleted_all == [super_admin_video.id]


@pytest.mark.http
def test_retry_video_processing_requires_super_admin_and_resets_outputs(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
    video_storage,
    video_processing_queue,
) -> None:
    owner = user_factory()
    admin = user_factory(role="admin")
    super_admin = user_factory(role="super_admin")
    video = video_repository.add(
        video_factory(
            owner_id=owner.id,
            processing_status=VideoProcessingStatus.PROCESSING,
            width=1920,
            height=1080,
            duration_seconds=12.5,
            thumbnail_path="thumbnails/video/thumbnail.jpg",
            variants=[make_video_variant()],
        )
    )
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: admin

    response = client.post(f"/videos/{video.id}/processing/retry")

    assert response.status_code == 403
    assert video_processing_queue.enqueued == []

    app.dependency_overrides[get_current_user] = lambda: super_admin
    response = client.post(f"/videos/{video.id}/processing/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["processing_status"] == "pending"
    assert body["width"] is None
    assert body["height"] is None
    assert body["duration_seconds"] is None
    assert body["thumbnail_path"] is None
    assert body["variants"] == []
    assert video_storage.deleted_processing_outputs == [video.id]
    assert video_repository.reset == [video.id]
    assert video_processing_queue.enqueued == [video.id]
    assert video_processing_queue.force_flags == [True]


@pytest.mark.http
def test_retry_video_processing_rejects_ready_video(
    app,
    client,
    user_factory,
    video_factory,
    video_repository,
    video_storage,
    video_processing_queue,
) -> None:
    super_admin = user_factory(role="super_admin")
    video = video_repository.add(
        video_factory(processing_status=VideoProcessingStatus.READY)
    )
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: super_admin

    response = client.post(f"/videos/{video.id}/processing/retry")

    assert response.status_code == 409
    assert response.json()["detail"] == "Video processing is already complete"
    assert video_storage.deleted_processing_outputs == []
    assert video_processing_queue.enqueued == []


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

    response = client.post(f"/interactions/videos/{video.id}/favorite")

    assert response.status_code == 204
    assert video_repository.is_favorite(video.id, user.id) is True

    response = client.get("/interactions/me/video-favorites")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == str(video.id)
    assert response.json()["items"][0]["download_url"] == f"/videos/{video.id}/download"
    assert response.json()["items"][0]["is_favorite"] is True

    response = client.delete(f"/interactions/videos/{video.id}/favorite")

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
        f"/interactions/videos/{video.id}/reactions",
        json={"reaction_type": "🔥"},
    )

    assert response.status_code == 200
    assert response.json()["reaction_type"] == "🔥"

    response = client.post(
        f"/interactions/videos/{video.id}/reactions",
        json={"reaction_type": "😂"},
    )

    assert response.status_code == 200

    response = client.post(
        f"/interactions/videos/{video.id}/reactions",
        json={"reaction_type": "😮"},
    )

    assert response.status_code == 409

    response = client.get(f"/interactions/videos/{video.id}/reactions")

    assert response.status_code == 200
    assert response.json() == [
        {"type": "🔥", "count": 1},
        {"type": "😂", "count": 1},
    ]

    response = client.delete(f"/interactions/videos/{video.id}/reactions")

    assert response.status_code == 204
    assert video_repository.get_reaction_counts(video.id) == {}
