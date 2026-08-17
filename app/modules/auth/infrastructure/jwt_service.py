from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.modules.users.domain.user import User
from config.settings import settings


class JwtService:
    def create_access_token(self, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "type": "access",
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def create_refresh_token(self, user: User) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days,
        )
        payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        return payload

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        return payload
