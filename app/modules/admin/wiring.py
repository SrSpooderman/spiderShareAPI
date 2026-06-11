from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.admin.infrastructure.queue import AdminQueueInspector, RqAdminQueueInspector
from app.modules.admin.infrastructure.read_model import AdminReadModel, SqlAlchemyAdminReadModel
from app.shared.infrastructure.db.session import get_db


def get_admin_queue_inspector() -> AdminQueueInspector:
    return RqAdminQueueInspector()


def get_admin_read_model(
    db: Session = Depends(get_db),
    queue_inspector: AdminQueueInspector = Depends(get_admin_queue_inspector),
) -> AdminReadModel:
    return SqlAlchemyAdminReadModel(db, queue_inspector)
