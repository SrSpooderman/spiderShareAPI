from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.shared.infrastructure.db.base import Base


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("scope", "user_id", "key", name="uq_idempotency_scope_user_key"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class IdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self,
        *,
        scope: str,
        user_id: str,
        key: str,
    ) -> IdempotencyRecordModel | None:
        statement = select(IdempotencyRecordModel).where(
            IdempotencyRecordModel.scope == scope,
            IdempotencyRecordModel.user_id == user_id,
            IdempotencyRecordModel.key == key,
        )
        return self.session.scalar(statement)

    def start(
        self,
        *,
        scope: str,
        user_id: str,
        key: str,
        request_hash: str,
    ) -> tuple[IdempotencyRecordModel, bool]:
        record = IdempotencyRecordModel(
            scope=scope,
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            status="processing",
        )
        self.session.add(record)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing_record = self.get(scope=scope, user_id=user_id, key=key)
            if existing_record is None:
                raise
            return existing_record, False
        self.session.refresh(record)
        return record, True

    def complete(
        self,
        record: IdempotencyRecordModel,
        *,
        response_status_code: int,
        response_body: dict,
    ) -> None:
        record.status = "completed"
        record.response_status_code = response_status_code
        record.response_body = response_body
        record.error_message = None
        self.session.commit()

    def fail(self, record: IdempotencyRecordModel, error_message: str) -> None:
        record.status = "failed"
        record.error_message = error_message
        self.session.commit()

    def delete(self, record: IdempotencyRecordModel) -> None:
        self.session.delete(record)
        self.session.commit()
