from fastapi import Depends
from sqlalchemy.orm import Session

from app.shared.infrastructure.db.session import get_db
from app.shared.infrastructure.idempotency import IdempotencyRepository


def get_idempotency_repository(
    db: Session = Depends(get_db),
) -> IdempotencyRepository:
    return IdempotencyRepository(db)
