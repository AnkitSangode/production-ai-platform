from sqlalchemy.orm import Session
from typing import Any

from app.repositories.document_repository import DocumentRepository
from app.repositories.outbox_repository import OutboxRepository


class UnitOfWork:
    def __init__(self, db: Session):
        self._db = db

        self.documents = DocumentRepository(db)
        self.outbox = OutboxRepository(db)

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def flush(self) -> None:
        self._db.flush()

    def refresh(self, entity: Any) -> None:
        self._db.refresh(entity)