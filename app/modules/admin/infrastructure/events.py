import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.admin.infrastructure.models import (
    AdminAuditEntryModel,
    WorkerEventModel,
)
from app.modules.users.domain.user import User


logger = logging.getLogger(__name__)


class AdminEventRecorder:
    def worker_event(
        self,
        *,
        event_type: str,
        message: str,
        level: str = "info",
        video_id: UUID | str | None = None,
        job_id: str | None = None,
        worker_name: str = "jaimito_worker",
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError

    def audit(
        self,
        *,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: UUID | str,
        result: str,
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError


class NullAdminEventRecorder(AdminEventRecorder):
    def worker_event(self, **_kwargs) -> None:
        return

    def audit(self, **_kwargs) -> None:
        return


class SqlAlchemyAdminEventRecorder(AdminEventRecorder):
    def __init__(self, session: Session) -> None:
        self.session = session

    def worker_event(
        self,
        *,
        event_type: str,
        message: str,
        level: str = "info",
        video_id: UUID | str | None = None,
        job_id: str | None = None,
        worker_name: str = "jaimito_worker",
        metadata: dict | None = None,
    ) -> None:
        self._safe_add(
            WorkerEventModel(
                event_type=event_type,
                level=level,
                message=message,
                video_id=str(video_id) if video_id is not None else None,
                job_id=job_id,
                worker_name=worker_name,
                metadata_json=metadata,
            )
        )

    def audit(
        self,
        *,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: UUID | str,
        result: str,
        metadata: dict | None = None,
    ) -> None:
        self._safe_add(
            AdminAuditEntryModel(
                actor_user_id=str(actor.id),
                actor_username=actor.username,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                result=result,
                metadata_json=metadata,
            )
        )

    def _safe_add(self, model) -> None:
        try:
            self.session.add(model)
            self.session.commit()
        except Exception:
            self.session.rollback()
            logger.exception("Failed to persist admin operational event")
