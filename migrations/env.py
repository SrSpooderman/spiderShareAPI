from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.shared.infrastructure.db.base import Base
from app.shared.infrastructure.idempotency import IdempotencyRecordModel
from config.settings import settings

# Models
from app.modules.admin.infrastructure.models import AdminAuditEntryModel, WorkerEventModel
from app.modules.steam.infrastructure.models import SteamGameModel
from app.modules.users.infrastructure.models import UserModel
from app.modules.videos.infrastructure.models import (
    VideoCategoryAssignmentModel,
    VideoCategoryModel,
    VideoFavoriteModel,
    VideoModel,
    VideoReactionModel,
    VideoTagAssignmentModel,
    VideoTagModel,
    VideoVariantModel,
)


config = context.config

config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
