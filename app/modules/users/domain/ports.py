from abc import ABC, abstractmethod
from uuid import UUID
from app.modules.users.domain.user import User, UserCreate


class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_uuid: UUID) -> User | None:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        pass

    @abstractmethod
    def list(self) -> list[User]:
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
        role: str | None = None,
        is_active: bool | None = None,
        clear_display_name: bool = False,
        clear_bio: bool = False,
        clear_avatar_image: bool = False,
    ) -> User | None:
        pass

    @abstractmethod
    def delete(self, user_uuid: UUID) -> bool:
        pass
