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
    user = user_factory(username="alice", role=UserRole.ADMIN)
    jwt_service = JwtService()

    token = jwt_service.create_access_token(user)
    payload = jwt_service.decode_access_token(token)

    assert payload["sub"] == str(user.id)
    assert payload["username"] == "alice"
    assert payload["role"] == "admin"
    assert "exp" in payload


@pytest.mark.unit
def test_jwt_service_raises_for_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret")
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    jwt_service = JwtService()

    with pytest.raises(JWTError):
        jwt_service.decode_access_token("not-a-valid-token")
