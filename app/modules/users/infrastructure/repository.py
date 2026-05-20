from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.domain.ports import UserRepository
from app.modules.users.domain.user import User, UserCreate
from app.modules.users.infrastructure.mappers import (
    user_create_to_model,
    user_model_to_domain,
)
from app.modules.users.infrastructure.models import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_uuid: UUID) -> User | None:
        statement = select(UserModel).where(UserModel.id == str(user_uuid))
        model = self.session.scalar(statement)

        if model is None:
            return None

        return user_model_to_domain(model)

    def get_by_username(self, username: str) -> User | None:
        statement = select(UserModel).where(UserModel.username == username)
        model = self.session.scalar(statement)

        if model is None:
            return None

        return user_model_to_domain(model)

    def list(self) -> list[User]:
        statement = select(UserModel).order_by(UserModel.created_at.desc())
        models = self.session.scalars(statement).all()

        return [user_model_to_domain(model) for model in models]

    def create(self, user: UserCreate) -> User:
        model = user_create_to_model(user)

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)

        return user_model_to_domain(model)

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
        statement = select(UserModel).where(UserModel.id == str(user_uuid))
        model = self.session.scalar(statement)

        if model is None:
            return None

        if username is not None:
            model.username = username
        if display_name is not None or clear_display_name:
            model.display_name = display_name
        if bio is not None or clear_bio:
            model.bio = bio
        if avatar_image is not None or clear_avatar_image:
            model.avatar_image = avatar_image
        if password_hash is not None:
            model.password_hash = password_hash
        if role is not None:
            model.role = role
        if is_active is not None:
            model.is_active = is_active

        self.session.commit()
        self.session.refresh(model)

        return user_model_to_domain(model)

    def delete(self, user_uuid: UUID) -> bool:
        statement = select(UserModel).where(UserModel.id == str(user_uuid))
        model = self.session.scalar(statement)

        if model is None:
            return False

        self.session.delete(model)
        self.session.commit()

        return True
