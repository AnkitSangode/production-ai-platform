from sqlalchemy.orm import Session
from app.db.models import Document
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, update


class DocumentRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, document: Document) -> Document:
        self.db.add(document)
        return document

    def claim_for_processing(
        self,
        *,
        document_id: UUID,
        worker_id: UUID,
        lease_expiry: datetime,
    ) -> bool:

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                or_(
                    Document.processing_worker_id.is_(None),
                    Document.processing_lease_expiry <= func.now(),
                ),
            )
            .values(
                processing_worker_id=worker_id,
                processing_lease_expiry=lease_expiry,
            )
        )

        result = self.db.execute(statement)

        return result.rowcount == 1
