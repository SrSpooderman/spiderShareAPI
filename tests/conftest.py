import pytest
from fastapi.testclient import TestClient

from app.bootstrap.app_factory import create_app
from tests.factories import make_steam_game, make_user
from tests.fakes import (
    FakeAccessTokenService,
    FakePasswordHasher,
    FakeSteamClient,
    FakeSteamGameRepository,
    FakeUserRepository,
)


@pytest.fixture
def user_factory():
    return make_user


@pytest.fixture
def steam_game_factory():
    return make_steam_game


@pytest.fixture
def user_repository():
    return FakeUserRepository()


@pytest.fixture
def steam_game_repository():
    return FakeSteamGameRepository()


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
def app():
    app = create_app()
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)
