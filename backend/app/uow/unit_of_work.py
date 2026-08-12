from sqlalchemy.orm import Session
from typing import Any

from app.repositories.document_repository import DocumentRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.user import UserRepository

class UnitOfWork:
    def __init__(self, db: Session):
        self._db = db

        self.documents = DocumentRepository(db)
        self.outbox = OutboxRepository(db)
        self.user = UserRepository(db)

    def commit(self) -> None:
        self._db.commit()

    def rollback(self) -> None:
        self._db.rollback()

    def flush(self) -> None:
        self._db.flush()

    def refresh(self, entity: Any) -> None:
        self._db.refresh(entity)

    def close(self) -> None:
        self._db.close()