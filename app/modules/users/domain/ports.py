from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID
from app.modules.users.domain.user import User, UserCreate


class UserPersistenceConflictError(Exception):
    pass


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_uuid: UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        pass

    @abstractmethod
    def get_by_oidc_subject(self, subject: str) -> User | None:
        pass

    @abstractmethod
    def list_users(self) -> list[User]:
        pass

    @abstractmethod
    def create(self, user: UserCreate) -> User:
        pass

    @abstractmethod
    def update(
        self,
        user_uuid: UUID,
        *,
        username: str | None = None,
        display_name: str | None = None,
        bio: str | None = None,
        avatar_image: bytes | None = None,
        password_hash: str | None = None,
        oidc_email: str | None = None,
        oidc_name: str | None = None,
        oidc_groups: list[str] | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        last_login_at: datetime | None = None,
        clear_display_name: bool = False,
        clear_bio: bool = False,
        clear_avatar_image: bool = False,
    ) -> User | None:
        pass

    @abstractmethod
    def delete(self, user_uuid: UUID) -> bool:
        pass
