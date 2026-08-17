import pytest
from jose import JWTError

from app.modules.auth.infrastructure.jwt_service import JwtService
from app.modules.users.domain.user import UserRole
from config.settings import settings


@pytest.mark.unit
def test_jwt_service_creates_decodable_access_token(
    monkeypatch,
    user_factory,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret")
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(settings, "access_token_expire_minutes", 15)
    monkeypatch.setattr(settings, "refresh_token_expire_days", 7)
    user = user_factory(username="alice", role=UserRole.ADMIN)
    jwt_service = JwtService()

    token = jwt_service.create_access_token(user)
    payload = jwt_service.decode_access_token(token)

    assert payload["sub"] == str(user.id)
    assert payload["username"] == "alice"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert "exp" in payload

    refresh_token = jwt_service.create_refresh_token(user)
    refresh_payload = jwt_service.decode_refresh_token(refresh_token)

    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"
    assert "exp" in refresh_payload


@pytest.mark.unit
def test_jwt_service_raises_for_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret")
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    jwt_service = JwtService()

    with pytest.raises(JWTError):
        jwt_service.decode_access_token("not-a-valid-token")


@pytest.mark.unit
def test_jwt_service_rejects_wrong_token_type(monkeypatch, user_factory) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret")
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    user = user_factory(username="alice")
    jwt_service = JwtService()

    refresh_token = jwt_service.create_refresh_token(user)
    access_token = jwt_service.create_access_token(user)

    with pytest.raises(ValueError):
        jwt_service.decode_access_token(refresh_token)

    with pytest.raises(ValueError):
        jwt_service.decode_refresh_token(access_token)
