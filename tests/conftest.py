import pytest
from fastapi.testclient import TestClient

from app.bootstrap.app_factory import create_app
from app.modules.videos.wiring import get_video_processing_queue
from app.shared.wiring import get_idempotency_repository
from tests.factories import make_steam_game, make_user, make_video
from tests.fakes import (
    FakeAccessTokenService,
    FakeIdempotencyRepository,
    FakePasswordHasher,
    FakeSteamClient,
    FakeSteamGridDbClient,
    FakeSteamGameRepository,
    FakeVideoCategoryRepository,
    FakeVideoProcessingQueue,
    FakeUserRepository,
    FakeVideoRepository,
    FakeVideoStorage,
    FakeVideoTagRepository,
    FakeVideoTranscoder,
)


@pytest.fixture
def user_factory():
    return make_user


@pytest.fixture
def steam_game_factory():
    return make_steam_game


@pytest.fixture
def video_factory():
    return make_video


@pytest.fixture
def user_repository():
    return FakeUserRepository()


@pytest.fixture
def steam_game_repository():
    return FakeSteamGameRepository()


@pytest.fixture
def video_repository():
    return FakeVideoRepository()


@pytest.fixture
def video_category_repository():
    return FakeVideoCategoryRepository()


@pytest.fixture
def video_tag_repository():
    return FakeVideoTagRepository()


@pytest.fixture
def video_storage():
    return FakeVideoStorage()


@pytest.fixture
def video_transcoder():
    return FakeVideoTranscoder()


@pytest.fixture
def video_processing_queue():
    return FakeVideoProcessingQueue()


@pytest.fixture
def idempotency_repository():
    return FakeIdempotencyRepository()


@pytest.fixture
def password_hasher():
    return FakePasswordHasher()


@pytest.fixture
def access_token_service():
    return FakeAccessTokenService()


@pytest.fixture
def steam_client():
    return FakeSteamClient()


@pytest.fixture
def steamgriddb_client():
    return FakeSteamGridDbClient()


@pytest.fixture
def app(video_processing_queue, idempotency_repository):
    app = create_app()
    app.dependency_overrides[get_video_processing_queue] = lambda: video_processing_queue
    app.dependency_overrides[get_idempotency_repository] = lambda: idempotency_repository
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)
