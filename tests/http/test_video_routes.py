import pytest

from app.modules.auth.wiring import get_current_user, get_optional_current_user
from app.modules.videos.wiring import (
    get_video_processing_queue,
    get_video_repository,
    get_video_storage,
)
from app.modules.videos.domain.video import VideoProcessingStatus
from tests.factories import make_video_category, make_video_tag, make_video_variant


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
    assert body["items"][0]["popularity_score"] == matching_high.favorite_count * 4

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
    user = user_factory()
    app.dependency_overrides[get_video_repository] = lambda: video_repository
    app.dependency_overrides[get_video_storage] = lambda: video_storage
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(
        "/videos",
        data={
            "title": "Boss clip",
            "description": "Context",
            "tags": ["boss", "clip"],
        },
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Boss clip"
    assert body["owner_id"] == str(user.id)
    assert body["original_filename"] == "clip.mp4"
    assert body["processing_status"] == "pending"
    assert body["width"] is None
    assert body["height"] is None
    assert body["duration_seconds"] is None
    assert body["thumbnail_path"] is None
    assert body["playback_url"] is None
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
                )
            ],
        )
    )
    original_path = tmp_path / "original.mp4"
    stream_path = tmp_path / "low_h264.mp4"
    thumbnail_path = tmp_path / "thumbnail.jpg"
    original_path.write_bytes(b"original-video")
    stream_path.write_bytes(b"stream-video")
    thumbnail_path.write_bytes(b"thumbnail")
    video_storage.original_paths[video.id] = original_path
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

    app.dependency_overrides[get_optional_current_user] = lambda: user
    response = client.get(f"/videos/{video.id}/download")

    assert response.status_code == 200


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
        json={"reaction_type": "🔥"},
    )

    assert response.status_code == 200
    assert response.json()["reaction_type"] == "🔥"

    response = client.post(
        f"/videos/{video.id}/reactions",
        json={"reaction_type": "😂"},
    )

    assert response.status_code == 200

    response = client.post(
        f"/videos/{video.id}/reactions",
        json={"reaction_type": "😮"},
    )

    assert response.status_code == 409

    response = client.get(f"/videos/{video.id}/reactions")

    assert response.status_code == 200
    assert response.json() == [
        {"type": "🔥", "count": 1},
        {"type": "😂", "count": 1},
    ]

    response = client.delete(f"/videos/{video.id}/reactions")

    assert response.status_code == 204
    assert video_repository.get_reaction_counts(video.id) == {}
