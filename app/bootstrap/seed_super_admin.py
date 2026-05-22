import logging

from sqlalchemy import select

from app.modules.auth.application.password_hasher import PasswordHasher
from app.modules.users.domain.user import UserRole
from app.modules.users.infrastructure.models import UserModel
from app.shared.infrastructure.db.session import SessionLocal
from app.shared.infrastructure.logging import configure_logging
from config.settings import settings


logger = logging.getLogger(__name__)


def seed_super_admin() -> None:
    username = settings.super_admin_username
    password = settings.super_admin_password

    if not username and not password:
        logger.info("Super admin credentials not configured; skipping seed")
        return

    if not username or not password:
        raise RuntimeError(
            "Both SUPER_ADMIN_USERNAME and SUPER_ADMIN_PASSWORD must be configured.",
        )

    with SessionLocal() as session:
        existing_super_admin = session.scalar(
            select(UserModel).where(UserModel.role == UserRole.SUPER_ADMIN.value),
        )
        if existing_super_admin is not None:
            logger.info("Super admin already exists; skipping seed")
            return

        existing_user = session.scalar(
            select(UserModel).where(UserModel.username == username),
        )
        if existing_user is not None:
            logger.warning(
                "Configured super admin username already exists; skipping seed",
            )
            return

        user = UserModel(
            username=username,
            password_hash=PasswordHasher().hash_password(password),
            ldap=False,
            role=UserRole.SUPER_ADMIN.value,
        )
        session.add(user)
        session.commit()

    logger.info("Super admin created")


if __name__ == "__main__":
    configure_logging()
    seed_super_admin()
